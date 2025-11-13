/**
 * {{SERVICE_NAME}} - Node.js Microservice Template
 *
 * {{SERVICE_DESCRIPTION}}
 */

const express = require('express');
const { v4: uuidv4 } = require('uuid');

const app = express();
const PORT = process.env.PORT || 8080;

// Middleware
app.use(express.json());

// RunContext middleware - inject or extract run_id
app.use((req, res, next) => {
  let runId = req.headers['x-run-id'];

  if (!runId) {
    // Generate new run_id
    const timestamp = new Date().toISOString().replace(/[-:]/g, '').slice(0, 14);
    const random = Math.random().toString(36).substring(2, 10);
    runId = `exec_${timestamp}_${random}`;
  }

  // Attach to request
  req.runId = runId;

  // Add to response
  res.setHeader('X-Run-ID', runId);

  next();
});

// Logging middleware
app.use((req, res, next) => {
  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    severity: 'INFO',
    run_id: req.runId,
    method: req.method,
    path: req.path,
    service: '{{SERVICE_NAME}}'
  }));
  next();
});

// Routes
app.get('/', (req, res) => {
  res.json({
    service: '{{SERVICE_NAME}}',
    version: '0.1.0',
    status: 'running'
  });
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

app.post('/graphql', async (req, res) => {
  const { query, variables } = req.body;

  // TODO: Implement GraphQL schema and resolvers

  res.json({
    data: {
      message: 'GraphQL endpoint ready',
      run_id: req.runId
    }
  });
});

// Example handler
app.post('/api/example', async (req, res) => {
  try {
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      severity: 'INFO',
      run_id: req.runId,
      message: 'Example handler called',
      data: req.body
    }));

    // Your business logic here
    const result = {
      success: true,
      data: req.body,
      run_id: req.runId
    };

    res.json(result);
  } catch (error) {
    console.error(JSON.stringify({
      timestamp: new Date().toISOString(),
      severity: 'ERROR',
      run_id: req.runId,
      error: error.message
    }));

    res.status(500).json({
      error: error.message,
      run_id: req.runId
    });
  }
});

// Error handler
app.use((err, req, res, next) => {
  console.error(JSON.stringify({
    timestamp: new Date().toISOString(),
    severity: 'ERROR',
    run_id: req.runId,
    error: err.message,
    stack: err.stack
  }));

  res.status(500).json({
    error: 'Internal server error',
    run_id: req.runId
  });
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    severity: 'INFO',
    message: `{{SERVICE_NAME}} listening on port ${PORT}`,
    service: '{{SERVICE_NAME}}'
  }));
});
