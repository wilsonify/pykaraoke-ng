# Integration Tests Quick Reference

## TL;DR - Run Tests Now

```bash
# Unit tests (local, no Docker needed)
./scripts/run-tests.sh

# Integration tests (requires Docker)
./test-docker.sh integration

# All tests together
./test-docker.sh all

# With coverage report
./test-docker.sh coverage
```

## What Changed

| Item | Before | After |
|------|--------|-------|
| Integration tests | ❌ SKIPPED | ✅ RUNNING |
| Backend server | Manual start | 🤖 Auto-orchestrated |
| HTTP endpoints tested | ❌ No | ✅ Yes |
| Docker setup | Basic | 🚀 Integration-enabled |

## Key Commands

```bash
# Quick integration test
./test-docker.sh integration

# Full suite with coverage
./test-docker.sh coverage

# Direct Docker Compose
cd deploy/docker
docker compose --profile integration run test-integration

# Check service status
docker compose ps

# View logs
docker compose logs backend-test
docker compose logs test-integration
```

## Files You May Want to Review

1. **[INTEGRATION_TESTS_SETUP.md](INTEGRATION_TESTS_SETUP.md)** - Summary of changes
2. **[DOCKER_INTEGRATION_ARCHITECTURE.md](DOCKER_INTEGRATION_ARCHITECTURE.md)** - Visual architecture
3. **[docs/development/integration-testing.md](docs/development/integration-testing.md)** - Complete guide
4. **[deploy/docker/docker-compose.yml](deploy/docker/docker-compose.yml)** - Service definitions
5. **[test-docker.sh](test-docker.sh)** - Convenience script

## How It Works

```
docker run backend     → Starts PyKaraoke server
     ↓ (healthcheck)
     ✓ healthy
     ↓
docker run tests       → Runs integration tests against server
     ↓
     ✓ All tests pass
```

## Integration Tests Now Included

- ✅ `test_health_endpoint()` - Backend is responding
- ✅ `test_state_endpoint()` - Can query player state
- ✅ `test_command_endpoint()` - Can send commands
- ✅ `test_events_endpoint()` - Can stream events
- ✅ `test_stdio_server_startup()` - Backend process starts
- ✅ `test_command_response_flow()` - Stdio communication works

## Backward Compatibility

✅ **All existing tests still work locally**

```bash
./scripts/run-tests.sh
# Results: 174 passed, 9 skipped (same as before)
```

The integration tests gracefully skip when server is not available.

## CI/CD Integration

Add to your CI pipeline:
```bash
./test-docker.sh all  # Runs everything
```

Exit code: 0 = success, non-zero = failure

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Backend not running" | Use `./test-docker.sh integration` |
| "Port 8080 in use" | Docker handles this automatically |
| "Tests taking too long" | First run builds images; cached runs are fast |
| "Service won't start" | Check `docker compose logs backend-test` |

## Performance

- **First run**: 2-5 minutes (builds Docker images)
- **Cached runs**: 15-30 seconds
- **Unit tests only**: ~5 seconds (no Docker)

## Next Steps

1. Try it out: `./test-docker.sh integration`
2. Read full guide: [integration-testing.md](docs/development/integration-testing.md)
3. Integrate with CI/CD
4. Share with team

---

**Questions?** See [INTEGRATION_TESTS_SETUP.md](INTEGRATION_TESTS_SETUP.md) or [docs/development/integration-testing.md](docs/development/integration-testing.md)
