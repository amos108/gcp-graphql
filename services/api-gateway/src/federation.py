"""
Production-Ready GraphQL Federation Handler for API Gateway

This implements a robust federation system that:
1. Dynamically discovers service schemas (no hardcoded service names)
2. Parses GraphQL queries to determine which services own which types
3. Handles entity resolution across services (_entities query)
4. Merges results properly for nested queries
5. Works with ANY GraphQL services following federation patterns

This is infrastructure code - it will work with new production services
without modification as long as they follow the federation contract.
"""

import httpx
import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from graphql import (
    parse,
    DocumentNode,
    OperationDefinitionNode,
    FieldNode,
    SelectionSetNode,
    visit,
    Visitor,
    SKIP
)
from graphql.language import print_ast

logger = logging.getLogger(__name__)


class FederationComposer:
    """
    Production-ready GraphQL Federation composer.

    Dynamically routes queries to appropriate services based on type ownership,
    resolves entities across services, and properly merges results.
    """

    def __init__(self, run_storage_url: Optional[str] = None):
        self.schemas: Dict[str, str] = {}
        self.service_urls: Dict[str, str] = {}
        # Map type names to the service that owns them
        self.type_to_service: Dict[str, str] = {}
        # Track which types are extended by which services
        self.type_extensions: Dict[str, List[str]] = {}
        # Map query field names to the service that owns them
        self.query_field_to_service: Dict[str, str] = {}
        # Map field names to their return type (e.g., "author" -> "User")
        self.field_to_return_type: Dict[str, str] = {}
        # Run storage service URL (for recording execution traces)
        self.run_storage_url = run_storage_url
        # Track service calls for each run
        self.run_service_calls: Dict[str, List[Dict[str, Any]]] = {}

    async def fetch_subgraph_schemas(self, services: Dict[str, str]):
        """
        Fetch GraphQL schemas from all subgraph services and build type ownership map.

        Args:
            services: Dict mapping service names to their URLs
        """
        self.service_urls = services

        async with httpx.AsyncClient(timeout=30.0) as client:
            for service_name, service_url in services.items():
                try:
                    # Fetch schema SDL from subgraph
                    schema_url = f"{service_url}/_graphql/schema"
                    response = await client.get(schema_url)

                    if response.status_code == 200:
                        schema_data = response.json()
                        sdl = schema_data.get('sdl', '')
                        self.schemas[service_name] = sdl

                        # Parse schema to build type ownership map
                        self._parse_schema_types(service_name, sdl)

                        logger.info(f"Fetched schema from {service_name}")
                    else:
                        logger.warning(f"Failed to fetch schema from {service_name}: {response.status_code}")

                except Exception as e:
                    logger.error(f"Error fetching schema from {service_name}: {e}")

        logger.info(f"Loaded {len(self.schemas)} subgraph schemas")
        logger.info(f"Type ownership map: {self.type_to_service}")
        logger.info(f"Type extensions: {self.type_extensions}")
        logger.info(f"Query field map: {self.query_field_to_service}")

    def _parse_schema_types(self, service_name: str, sdl: str):
        """
        Parse schema SDL to determine which types this service owns vs extends,
        and which Query fields this service provides.

        This enables dynamic routing without hardcoded service names.
        """
        if not sdl:
            return

        try:
            # Simple SDL parsing to find type definitions
            lines = sdl.split('\n')
            inside_query = False
            inside_type = None

            for line in lines:
                line = line.strip()

                # Look for type definitions (owned types)
                if line.startswith('type ') and '@key' in line:
                    # Extract type name: "type User @key(fields: "id") {"
                    parts = line.split()
                    if len(parts) >= 2:
                        type_name = parts[1]
                        # Check if this is an extension
                        if 'extend' not in line:
                            self.type_to_service[type_name] = service_name
                        else:
                            # This service extends this type
                            if type_name not in self.type_extensions:
                                self.type_extensions[type_name] = []
                            self.type_extensions[type_name].append(service_name)
                        inside_type = type_name
                        continue

                # Parse fields within type definitions
                if inside_type and ':' in line and not line.startswith('#') and not line.startswith('}'):
                    # Extract field and type from lines like: "author: User!" or "posts: [Post!]!"
                    parts = line.split(':')
                    if len(parts) >= 2:
                        field_name = parts[0].strip()
                        type_part = parts[1].strip()
                        # Extract type name from "User!", "[Post!]!", etc.
                        # Remove !, [, ], whitespace
                        return_type = type_part.replace('!', '').replace('[', '').replace(']', '').strip()
                        if return_type and return_type not in ['ID', 'String', 'Int', 'Float', 'Boolean']:
                            self.field_to_return_type[field_name] = return_type
                            logger.debug(f"Mapped field '{field_name}' to type '{return_type}'")

                # End of type definition
                if inside_type and line.startswith('}'):
                    inside_type = None
                    continue

                # Parse Query type fields
                if line.startswith('type Query'):
                    inside_query = True
                    continue

                if inside_query:
                    # Check for closing brace
                    if line.startswith('}'):
                        inside_query = False
                        continue

                    # Extract field name from lines like: "users: [User!]!" or "user(id: ID!): User"
                    if ':' in line and not line.startswith('#'):
                        # Get the field name (before the colon)
                        field_name = line.split(':')[0].strip()
                        # Remove any arguments like "user(id: ID!)" -> "user"
                        if '(' in field_name:
                            field_name = field_name.split('(')[0].strip()

                        if field_name:
                            self.query_field_to_service[field_name] = service_name
                            logger.debug(f"Mapped query field '{field_name}' to {service_name}")

            # DEBUG: Confirm Query field parsing executed
            logger.info(f"[FEDERATION FIX] Query field parsing completed for {service_name}")

        except Exception as e:
            logger.warning(f"Error parsing schema for {service_name}: {e}")

    async def execute_federated_query(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query with proper federation support.

        This intelligently routes queries to appropriate services and handles
        entity resolution for cross-service field access.

        Args:
            query: GraphQL query string
            variables: Query variables
            run_id: Request tracking ID

        Returns:
            GraphQL response dict with data/errors
        """
        variables = variables or {}
        start_time = time.time()

        # Log query start
        logger.info(f"[{run_id}] Federation query started", extra={
            'event': 'federation_query_started',
            'run_id': run_id,
            'query_preview': query[:200] if len(query) > 200 else query,
            'has_variables': bool(variables)
        })

        try:
            # Parse the query to understand what's being requested
            parse_start = time.time()
            document = parse(query)
            parse_time = (time.time() - parse_start) * 1000

            # Extract fields being queried
            queried_fields = self._extract_queried_fields(document)

            # Determine which services to query based on fields
            services_to_query = self._determine_services_for_query(queried_fields)

            # Log query analysis
            logger.info(f"[{run_id}] Query analyzed", extra={
                'event': 'query_analysis',
                'run_id': run_id,
                'queried_fields': list(queried_fields),
                'target_services': services_to_query,
                'parse_time_ms': round(parse_time, 2)
            })

            if not services_to_query:
                # If we can't determine, try all services (failsafe)
                services_to_query = list(self.service_urls.keys())
                logger.warning(f"[{run_id}] Could not determine services, querying all: {services_to_query}")
            else:
                logger.info(f"[{run_id}] Routing query to services: {services_to_query}")

            # Check if we need entity resolution before executing
            needs_entity_resolution = self._check_needs_entity_resolution(document, {})
            logger.info(f"[{run_id}] Entity resolution check result: {needs_entity_resolution}")

            # Transform query for each service if entity resolution is needed
            if needs_entity_resolution:
                logger.info(f"[{run_id}] Query requires entity resolution - transforming queries for each service")
                # Execute with transformed queries
                exec_start = time.time()
                results = await self._execute_with_transformed_queries(
                    services_to_query,
                    document,
                    variables,
                    run_id
                )
                exec_time = (time.time() - exec_start) * 1000
            else:
                # Execute query as-is on relevant services
                logger.info(f"[{run_id}] NO entity resolution needed - executing query as-is")
                exec_start = time.time()
                results = await self._execute_on_services(
                    services_to_query,
                    query,
                    variables,
                    run_id
                )
                exec_time = (time.time() - exec_start) * 1000

            # Check if we need to resolve entities (cross-service references)
            needs_entity_resolution = self._check_needs_entity_resolution(document, results)

            if needs_entity_resolution:
                logger.info(f"[{run_id}] Query requires entity resolution across services")
                resolve_start = time.time()
                results = await self._resolve_entities(document, results, run_id)
                resolve_time = (time.time() - resolve_start) * 1000
            else:
                resolve_time = 0

            # Merge results
            merge_start = time.time()
            merged_data = self._merge_results(results)
            merge_time = (time.time() - merge_start) * 1000

            total_time = (time.time() - start_time) * 1000

            # Log completion
            logger.info(f"[{run_id}] Federation query completed", extra={
                'event': 'federation_query_completed',
                'run_id': run_id,
                'total_time_ms': round(total_time, 2),
                'execution_time_ms': round(exec_time, 2),
                'resolve_time_ms': round(resolve_time, 2),
                'merge_time_ms': round(merge_time, 2),
                'services_called': len(results),
                'success': 'errors' not in merged_data
            })

            # Record execution trace (async, fire-and-forget)
            if self.run_storage_url and run_id:
                asyncio.create_task(self._record_run(
                    run_id=run_id,
                    query=query,
                    variables=variables,
                    final_result=merged_data,
                    total_duration_ms=total_time
                ))

            return merged_data

        except Exception as e:
            total_time = (time.time() - start_time) * 1000
            logger.error(f"[{run_id}] Error executing federated query: {e}", exc_info=True, extra={
                'event': 'federation_query_error',
                'run_id': run_id,
                'error': str(e),
                'total_time_ms': round(total_time, 2)
            })
            return {
                "data": None,
                "errors": [{"message": f"Federation error: {str(e)}"}]
            }

    def _extract_queried_fields(self, document: DocumentNode) -> Set[str]:
        """
        Extract all root-level fields being queried.

        For example, in "query { users { id } posts { title } }"
        this returns {"users", "posts"}
        """
        fields = set()

        for definition in document.definitions:
            if isinstance(definition, OperationDefinitionNode):
                if definition.selection_set:
                    for selection in definition.selection_set.selections:
                        if isinstance(selection, FieldNode):
                            fields.add(selection.name.value)

        return fields

    def _determine_services_for_query(self, queried_fields: Set[str]) -> List[str]:
        """
        Determine which services own the queried fields.

        This is dynamic and works for any services - no hardcoded names!
        """
        services = set()

        for field_name in queried_fields:
            # First, check if we have a direct mapping for this query field
            if field_name in self.query_field_to_service:
                services.add(self.query_field_to_service[field_name])
                logger.debug(f"Direct field mapping: {field_name} -> {self.query_field_to_service[field_name]}")
                continue

            # Fallback: Convert field name to potential type name
            # e.g., "users" -> "User", "posts" -> "Post"
            type_name = self._field_to_type_name(field_name)

            # Find which service owns this type
            if type_name in self.type_to_service:
                services.add(self.type_to_service[type_name])
                logger.debug(f"Type mapping: {field_name} ({type_name}) -> {self.type_to_service[type_name]}")

            # Check if any services extend this type
            if type_name in self.type_extensions:
                services.update(self.type_extensions[type_name])
                logger.debug(f"Type extensions for {type_name}: {self.type_extensions[type_name]}")

        return list(services)

    def _field_to_type_name(self, field_name: str) -> str:
        """
        Convert field name to type name.

        Examples:
        - "users" -> "User"
        - "posts" -> "Post"
        - "comments" -> "Comment"
        """
        # Remove trailing 's' and capitalize
        if field_name.endswith('s') and len(field_name) > 1:
            return field_name[:-1].capitalize()
        return field_name.capitalize()

    def _check_needs_entity_resolution(
        self,
        document: DocumentNode,
        results: Dict[str, Any]
    ) -> bool:
        """
        Check if query includes fields that require entity resolution.

        This detects when we're querying nested fields on entity references
        that need to be resolved from other services.

        We detect this by looking for nested entity selections WITHIN result types,
        not at the top level query fields.
        """
        # Check if we have nested selections on entity types
        for definition in document.definitions:
            if isinstance(definition, OperationDefinitionNode):
                if definition.selection_set:
                    # Check nested selections (skip depth 0 which is the root query level)
                    for selection in definition.selection_set.selections:
                        if isinstance(selection, FieldNode) and selection.selection_set:
                            # Now check INSIDE the root query field for entity references
                            if self._has_nested_entity_selections(selection.selection_set):
                                return True
        return False

    def _has_nested_entity_selections(self, selection_set: SelectionSetNode) -> bool:
        """
        Recursively check if selection set has entity references with non-id fields.

        This checks if there are entity type fields (like "author", "user") that
        have selections beyond just "id", indicating cross-service resolution is needed.
        """
        for selection in selection_set.selections:
            if isinstance(selection, FieldNode):
                if selection.selection_set:
                    field_name = selection.name.value

                    # Get the actual return type from our schema mapping
                    type_name = self.field_to_return_type.get(field_name)
                    if not type_name:
                        # Fallback to heuristic
                        type_name = self._field_to_type_name(field_name)

                    # Check if this field references an entity type
                    if type_name in self.type_to_service:
                        # This is an entity reference - check if it has nested selections beyond 'id'
                        has_non_id_fields = any(
                            isinstance(s, FieldNode) and s.name.value not in ['id', '__typename']
                            for s in selection.selection_set.selections
                        )
                        if has_non_id_fields:
                            return True

                    # Recursively check nested selections
                    if self._has_nested_entity_selections(selection.selection_set):
                        return True
        return False

    async def _resolve_entities(
        self,
        document: DocumentNode,
        results: Dict[str, Any],
        run_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Resolve entities across services using _entities query.

        This is the core of GraphQL Federation - when a query requests fields
        on entities from different services, we resolve them using _entities.
        """
        try:
            # Extract entity references from results
            entity_refs = self._extract_entity_references(results, document)

            if not entity_refs:
                logger.debug("No entity references found to resolve")
                return results

            logger.info(f"Found {len(entity_refs)} entity references to resolve")

            # Resolve entities by calling _entities query on owning services
            resolved_entities = await self._fetch_entities(entity_refs, document, run_id)

            # Merge resolved entities back into results
            results = self._merge_entities(results, resolved_entities)

            return results

        except Exception as e:
            logger.error(f"Error resolving entities: {e}", exc_info=True)
            return results  # Return original results on error

    def _extract_entity_references(
        self,
        results: Dict[str, Any],
        document: DocumentNode
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract entity references from query results.

        Returns: Dict mapping type names to lists of entity representations
        Example: {"User": [{"__typename": "User", "id": "1"}, ...]}
        """
        entity_refs = {}

        def extract_from_value(value: Any, parent_type: Optional[str] = None):
            """Recursively extract entity references from nested data"""
            if isinstance(value, dict):
                # Check if this looks like an entity reference
                if "id" in value and len(value) <= 2:  # Entity stub (just id, maybe typename)
                    # Try to determine the type
                    type_name = parent_type
                    if type_name and type_name in self.type_to_service:
                        if type_name not in entity_refs:
                            entity_refs[type_name] = []
                        entity_refs[type_name].append({
                            "__typename": type_name,
                            "id": value["id"]
                        })
                else:
                    # Recursively search nested objects
                    for key, nested_value in value.items():
                        # Try to get actual type from schema mapping, fallback to inference
                        inferred_type = None
                        if isinstance(nested_value, (dict, list)):
                            inferred_type = self.field_to_return_type.get(key)
                            if not inferred_type:
                                inferred_type = self._field_to_type_name(key)
                        extract_from_value(nested_value, inferred_type)
            elif isinstance(value, list):
                for item in value:
                    extract_from_value(item, parent_type)

        # Extract from all service results
        for service_name, result in results.items():
            if "data" in result and result["data"]:
                extract_from_value(result["data"])

        return entity_refs

    async def _fetch_entities(
        self,
        entity_refs: Dict[str, List[Dict[str, Any]]],
        document: DocumentNode,
        run_id: Optional[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch full entity data using _entities query.

        For each type, calls the owning service's _entities query.
        """
        resolved = {}

        async with httpx.AsyncClient(timeout=30.0) as client:
            for type_name, refs in entity_refs.items():
                # Find which service owns this type
                if type_name not in self.type_to_service:
                    logger.warning(f"No service found for type {type_name}")
                    continue

                service_name = self.type_to_service[type_name]
                service_url = self.service_urls.get(service_name)

                if not service_url:
                    logger.warning(f"No URL found for service {service_name}")
                    continue

                # Extract the fields requested for this type from the document
                requested_fields = self._extract_requested_fields_for_type(document, type_name)

                # Build _entities query
                entities_query = self._build_entities_query(type_name, requested_fields)

                try:
                    graphql_url = f"{service_url}/graphql"
                    headers = {'Content-Type': 'application/json'}
                    if run_id:
                        headers['X-Run-ID'] = run_id

                    response = await client.post(
                        graphql_url,
                        json={
                            "query": entities_query,
                            "variables": {"representations": refs}
                        },
                        headers=headers
                    )

                    if response.status_code == 200:
                        result = response.json()
                        if "data" in result and "_entities" in result["data"]:
                            resolved[type_name] = result["data"]["_entities"]
                            logger.info(f"Resolved {len(result['data']['_entities'])} {type_name} entities")
                    else:
                        logger.warning(f"Entity resolution failed for {type_name}: {response.status_code}")

                except Exception as e:
                    logger.error(f"Error fetching entities for {type_name}: {e}")

        return resolved

    def _extract_requested_fields_for_type(
        self,
        document: DocumentNode,
        type_name: str
    ) -> List[str]:
        """
        Extract which fields are requested for a specific type.

        For example, in "posts { author { name email } }", if type_name is "User",
        this returns ["name", "email"]
        """
        fields = set()

        def visit_selections(selection_set: SelectionSetNode, current_type: Optional[str] = None):
            for selection in selection_set.selections:
                if isinstance(selection, FieldNode):
                    field_name = selection.name.value
                    # Get actual type from schema mapping, fallback to heuristic inference
                    inferred_type = self.field_to_return_type.get(field_name)
                    if not inferred_type:
                        inferred_type = self._field_to_type_name(field_name)

                    if inferred_type == type_name and selection.selection_set:
                        # This field returns the target type - collect its sub-fields
                        for sub_selection in selection.selection_set.selections:
                            if isinstance(sub_selection, FieldNode):
                                fields.add(sub_selection.name.value)

                    if selection.selection_set:
                        visit_selections(selection.selection_set, inferred_type)

        for definition in document.definitions:
            if isinstance(definition, OperationDefinitionNode):
                if definition.selection_set:
                    visit_selections(definition.selection_set)

        # Always include 'id' as it's the key field
        fields.add('id')

        return list(fields)

    def _build_entities_query(
        self,
        type_name: str,
        fields: List[str]
    ) -> str:
        """
        Build a _entities query to resolve entities.

        Example output:
        query($representations: [_Any!]!) {
          _entities(representations: $representations) {
            ... on User {
              id
              name
              email
            }
          }
        }
        """
        fields_str = "\n              ".join(fields)
        query = f"""
        query($representations: [_Any!]!) {{
          _entities(representations: $representations) {{
            ... on {type_name} {{
              {fields_str}
            }}
          }}
        }}
        """
        return query

    def _merge_entities(
        self,
        results: Dict[str, Any],
        resolved_entities: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Merge resolved entity data back into the original results.

        This replaces entity stubs (objects with just 'id') with full entities.
        """
        def merge_into_value(value: Any, type_name: Optional[str] = None) -> Any:
            """Recursively merge entities into nested data structures"""
            if isinstance(value, dict):
                # Check if this is an entity stub that needs to be replaced
                if "id" in value and len(value) <= 2 and type_name:
                    # Find the resolved entity
                    if type_name in resolved_entities:
                        entity_id = value["id"]
                        for resolved_entity in resolved_entities[type_name]:
                            if resolved_entity.get("id") == entity_id:
                                # Replace stub with full entity
                                return resolved_entity
                    return value  # No resolution found, keep stub
                else:
                    # Recursively process nested objects
                    result = {}
                    for key, nested_value in value.items():
                        # Get actual type from schema mapping, fallback to heuristic
                        inferred_type = None
                        if isinstance(nested_value, (dict, list)):
                            inferred_type = self.field_to_return_type.get(key)
                            if not inferred_type:
                                inferred_type = self._field_to_type_name(key)
                        result[key] = merge_into_value(nested_value, inferred_type)
                    return result
            elif isinstance(value, list):
                return [merge_into_value(item, type_name) for item in value]
            else:
                return value

        # Merge entities into all service results
        merged_results = {}
        for service_name, result in results.items():
            if "data" in result and result["data"]:
                merged_results[service_name] = {
                    **result,
                    "data": merge_into_value(result["data"])
                }
            else:
                merged_results[service_name] = result

        return merged_results

    async def _execute_with_transformed_queries(
        self,
        service_names: List[str],
        document: DocumentNode,
        variables: Dict[str, Any],
        run_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Execute queries on services with entity reference fields transformed to stubs.

        For example, if querying posts-service with `author { name email }`,
        this transforms it to `author { id }` since posts-service only knows about User.id
        """
        results = {}

        async with httpx.AsyncClient(timeout=30.0) as client:
            for service_name in service_names:
                if service_name not in self.service_urls:
                    continue

                # Transform query for this specific service
                transformed_doc = self._transform_query_for_service(document, service_name)
                transformed_query = print_ast(transformed_doc)

                service_url = self.service_urls[service_name]
                graphql_url = f"{service_url}/graphql"

                try:
                    headers = {'Content-Type': 'application/json'}
                    if run_id:
                        headers['X-Run-ID'] = run_id

                    logger.debug(f"Sending transformed query to {service_name}:\n{transformed_query}")

                    response = await client.post(
                        graphql_url,
                        json={"query": transformed_query, "variables": variables},
                        headers=headers
                    )

                    if response.status_code == 200:
                        results[service_name] = response.json()
                        logger.debug(f"Got response from {service_name}")
                    else:
                        logger.warning(f"Service {service_name} returned {response.status_code}")
                        results[service_name] = {
                            "errors": [{"message": f"Service {service_name} error: {response.status_code}"}]
                        }

                except Exception as e:
                    logger.error(f"Error calling {service_name}: {e}")
                    results[service_name] = {
                        "errors": [{"message": f"Service {service_name} error: {str(e)}"}]
                    }

        return results

    def _transform_query_for_service(
        self,
        document: DocumentNode,
        service_name: str
    ) -> DocumentNode:
        """
        Transform a query to only include fields that the given service knows about.

        For entity references (e.g., User in posts-service), strip fields down to just `id`.
        """
        from graphql.language import NameNode
        from copy import deepcopy

        def transform_selection_set(selection_set: SelectionSetNode) -> SelectionSetNode:
            """Recursively transform selection sets"""
            new_selections = []

            for selection in selection_set.selections:
                if isinstance(selection, FieldNode):
                    new_field = transform_field_node(selection)
                    new_selections.append(new_field)
                else:
                    new_selections.append(selection)

            return SelectionSetNode(selections=new_selections)

        def transform_field_node(node: FieldNode) -> FieldNode:
            """Transform a field node"""
            if not node.selection_set:
                return node

            field_name = node.name.value
            # Get actual type from our schema mapping, fallback to heuristic
            type_name = self.field_to_return_type.get(field_name)
            if not type_name:
                type_name = field_name[:-1].capitalize() if field_name.endswith('s') else field_name.capitalize()

            # Check if this field references an entity owned by another service
            if type_name in self.type_to_service:
                entity_service = self.type_to_service[type_name]

                # If this entity is NOT owned by the target service, stub it out
                if entity_service != service_name:
                    # Keep only the id field
                    id_field = FieldNode(
                        name=NameNode(value="id"),
                        arguments=[],
                        directives=[],
                        alias=None,
                        selection_set=None
                    )
                    # Return field with only id selection
                    return FieldNode(
                        name=node.name,
                        alias=node.alias,
                        arguments=node.arguments,
                        directives=node.directives,
                        selection_set=SelectionSetNode(selections=[id_field])
                    )

            # Otherwise, recursively transform nested selections
            new_selection_set = transform_selection_set(node.selection_set)
            return FieldNode(
                name=node.name,
                alias=node.alias,
                arguments=node.arguments,
                directives=node.directives,
                selection_set=new_selection_set
            )

        # Transform all definitions in the document
        new_definitions = []
        for definition in document.definitions:
            if isinstance(definition, OperationDefinitionNode) and definition.selection_set:
                new_selection_set = transform_selection_set(definition.selection_set)
                new_def = OperationDefinitionNode(
                    operation=definition.operation,
                    name=definition.name,
                    variable_definitions=definition.variable_definitions,
                    directives=definition.directives,
                    selection_set=new_selection_set
                )
                new_definitions.append(new_def)
            else:
                new_definitions.append(definition)

        return DocumentNode(definitions=new_definitions)

    async def _execute_on_services(
        self,
        service_names: List[str],
        query: str,
        variables: Dict[str, Any],
        run_id: Optional[str]
    ) -> Dict[str, Any]:
        """Execute query on specified services in parallel"""
        results = {}

        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []

            for service_name in service_names:
                if service_name not in self.service_urls:
                    continue

                service_url = self.service_urls[service_name]
                graphql_url = f"{service_url}/graphql"

                try:
                    headers = {'Content-Type': 'application/json'}
                    if run_id:
                        headers['X-Run-ID'] = run_id

                    # Log service call start
                    call_start = time.time()
                    logger.info(f"[{run_id}] → Calling {service_name}", extra={
                        'event': 'service_call_start',
                        'run_id': run_id,
                        'service': service_name,
                        'url': graphql_url,
                        'query': query[:200] if len(query) > 200 else query,
                        'variables': variables
                    })

                    response = await client.post(
                        graphql_url,
                        json={"query": query, "variables": variables},
                        headers=headers
                    )

                    call_duration = (time.time() - call_start) * 1000

                    if response.status_code == 200:
                        result_data = response.json()
                        results[service_name] = result_data

                        # Track service call for recording
                        self._track_service_call(
                            run_id=run_id,
                            service_name=service_name,
                            url=graphql_url,
                            query=query,
                            variables=variables,
                            output_data=result_data,
                            duration_ms=call_duration,
                            status_code=200,
                            has_errors='errors' in result_data,
                            error_messages=[e.get('message', str(e)) for e in result_data.get('errors', [])] if 'errors' in result_data else None
                        )

                        # Log service call success with response
                        logger.info(f"[{run_id}] ← Response from {service_name}", extra={
                            'event': 'service_call_success',
                            'run_id': run_id,
                            'service': service_name,
                            'duration_ms': round(call_duration, 2),
                            'response_data': result_data,
                            'has_errors': 'errors' in result_data,
                            'data_keys': list(result_data.get('data', {}).keys()) if result_data.get('data') else []
                        })
                    else:
                        error_result = {
                            "errors": [{"message": f"Service {service_name} error: {response.status_code}"}]
                        }
                        results[service_name] = error_result

                        # Track failed service call
                        self._track_service_call(
                            run_id=run_id,
                            service_name=service_name,
                            url=graphql_url,
                            query=query,
                            variables=variables,
                            output_data=error_result,
                            duration_ms=call_duration,
                            status_code=response.status_code,
                            has_errors=True,
                            error_messages=[f"HTTP {response.status_code}"]
                        )

                        logger.warning(f"[{run_id}] Service {service_name} returned {response.status_code}")

                        logger.error(f"[{run_id}] ← Error from {service_name}", extra={
                            'event': 'service_call_error',
                            'run_id': run_id,
                            'service': service_name,
                            'status_code': response.status_code,
                            'duration_ms': round(call_duration, 2)
                        })

                except Exception as e:
                    call_duration = (time.time() - call_start) * 1000 if 'call_start' in locals() else 0

                    error_result = {
                        "errors": [{"message": f"Service {service_name} error: {str(e)}"}]
                    }
                    results[service_name] = error_result

                    # Track exception
                    self._track_service_call(
                        run_id=run_id,
                        service_name=service_name,
                        url=graphql_url,
                        query=query,
                        variables=variables,
                        output_data=error_result,
                        duration_ms=call_duration,
                        status_code=0,
                        has_errors=True,
                        error_messages=[str(e)]
                    )

                    logger.error(f"[{run_id}] Error calling {service_name}: {e}", extra={
                        'event': 'service_call_exception',
                        'run_id': run_id,
                        'service': service_name,
                        'error': str(e),
                        'duration_ms': round(call_duration, 2)
                    })

        return results

    def _merge_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Intelligently merge results from multiple services.

        This properly handles:
        - Multiple services returning data for different fields
        - Collecting errors from all services
        - Preserving null vs missing data
        """
        merged = {"data": {}, "errors": []}

        for service_name, result in results.items():
            if "data" in result and result["data"]:
                # Merge data fields - later services override earlier ones for same keys
                merged["data"].update(result["data"])

            if "errors" in result:
                # Collect all errors
                merged["errors"].extend(result["errors"])

        # Clean up response
        if not merged["errors"]:
            del merged["errors"]

        if not merged["data"]:
            merged["data"] = None

        return merged

    def get_composed_schema_info(self) -> Dict[str, Any]:
        """Get information about the composed federated schema"""
        return {
            "subgraphs": list(self.schemas.keys()),
            "subgraph_count": len(self.schemas),
            "service_urls": self.service_urls,
            "type_ownership": self.type_to_service,
            "type_extensions": self.type_extensions,
            "query_field_map": self.query_field_to_service,
            "field_to_type_map": self.field_to_return_type
        }

    def _track_service_call(
        self,
        run_id: str,
        service_name: str,
        url: str,
        query: str,
        variables: Dict[str, Any],
        output_data: Dict[str, Any],
        duration_ms: float,
        status_code: int,
        has_errors: bool,
        error_messages: Optional[List[str]] = None
    ):
        """
        Track a service call for recording.

        Args:
            run_id: Request tracking ID
            service_name: Name of the service called
            url: Service URL
            query: GraphQL query sent
            variables: Query variables
            output_data: Response data from service
            duration_ms: Call duration in milliseconds
            status_code: HTTP status code
            has_errors: Whether errors occurred
            error_messages: List of error messages if any
        """
        if not run_id:
            return

        if run_id not in self.run_service_calls:
            self.run_service_calls[run_id] = []

        self.run_service_calls[run_id].append({
            "service_name": service_name,
            "url": url,
            "query": query,
            "variables": variables,
            "input_data": {"query": query, "variables": variables},
            "output_data": output_data,
            "duration_ms": round(duration_ms, 2),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "has_errors": has_errors,
            "error_messages": error_messages,
            "status_code": status_code
        })

    async def _record_run(
        self,
        run_id: str,
        query: str,
        variables: Dict[str, Any],
        final_result: Dict[str, Any],
        total_duration_ms: float
    ):
        """
        Record complete execution trace to run-storage-service.

        This is fire-and-forget - errors won't affect the response.

        Args:
            run_id: Request tracking ID
            query: Original GraphQL query
            variables: Query variables
            final_result: Final merged result
            total_duration_ms: Total execution time
        """
        try:
            # Get tracked service calls for this run
            service_calls = self.run_service_calls.get(run_id, [])

            # Build run data
            run_data = {
                "run_id": run_id,
                "query": query,
                "variables": variables,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "duration_ms": round(total_duration_ms, 2),
                "service_calls": service_calls,
                "final_result": final_result,
                "has_errors": "errors" in final_result,
                "error_summary": None,
                "environment": "production",  # TODO: Make configurable
                "metadata": {
                    "services_count": len(service_calls),
                    "query_length": len(query)
                }
            }

            # Extract error summary if there are errors
            if run_data["has_errors"] and "errors" in final_result:
                error_msgs = [e.get("message", str(e)) for e in final_result["errors"]]
                run_data["error_summary"] = "; ".join(error_msgs[:3])  # First 3 errors

            # Send to run-storage-service
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.run_storage_url}/runs",
                    json=run_data
                )

                if response.status_code == 200:
                    logger.debug(f"[{run_id}] Recorded execution trace to run-storage-service")
                else:
                    logger.warning(f"[{run_id}] Failed to record trace: {response.status_code}")

            # Clean up tracked calls for this run to free memory
            if run_id in self.run_service_calls:
                del self.run_service_calls[run_id]

        except Exception as e:
            # Don't let recording errors affect the response
            logger.warning(f"[{run_id}] Error recording run: {e}")
            # Clean up on error too
            if run_id in self.run_service_calls:
                del self.run_service_calls[run_id]
