"""
GraphQL resolvers for {{SERVICE_NAME}}

Add your business logic here.
"""

from playground_sdk import handler, RunContext, router, get_logger

logger = get_logger(__name__)


@handler
async def example_query(run: RunContext, id: int):
    """
    Example query handler.

    Args:
        run: RunContext with run_id for tracing
        id: Example parameter

    Returns:
        Query result
    """
    logger.info(f"Example query called with id={id}, run_id={run.run_id}")

    # Your query logic here
    result = {
        "id": id,
        "message": f"This is example data for id {id}",
        "run_id": run.run_id
    }

    return result


@handler
async def example_mutation(run: RunContext, data: dict):
    """
    Example mutation handler.

    Args:
        run: RunContext with run_id for tracing
        data: Input data

    Returns:
        Mutation result
    """
    logger.info(f"Example mutation called, run_id={run.run_id}")

    # Example: Call another service
    # db_result = await router.call_service('db-service', '''
    #     mutation {
    #         insert(table: "example", data: $data) {
    #             id
    #         }
    #     }
    # ''', {'data': data})

    # Your mutation logic here
    result = {
        "success": True,
        "data": data,
        "run_id": run.run_id
    }

    return result


# Export resolvers
resolvers = {
    'Query': {
        'exampleQuery': example_query
    },
    'Mutation': {
        'exampleMutation': example_mutation
    }
}
