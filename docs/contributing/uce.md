# Compliance (UCE)

The **Universal Compliance Engine** enforces StateWeave's architectural standards via 10 automated scanners.

## Running UCE

```bash
# Local
python scripts/uce.py

# CI mode (JSON output, exit 1 on failure)
python scripts/uce.py --mode=CI --json
```

## Scanners

| Scanner | What It Checks | Mode |
|---------|---------------|------|
| `schema_integrity` | Universal Schema models have required fields | BLOCK |
| `adapter_contract` | All adapters implement the full ABC | BLOCK |
| `serialization_safety` | No raw pickle/json.dumps outside serializer | BLOCK |
| `encryption_compliance` | All crypto goes through EncryptionFacade | BLOCK |
| `mcp_protocol` | MCP server has all required tools | BLOCK |
| `import_discipline` | No cross-layer imports | BLOCK |
| `logger_naming` | All loggers use `stateweave.*` convention | BLOCK |
| `test_coverage_gate` | Minimum test file coverage ratio | BLOCK |
| `file_architecture` | No orphan files outside MANIFEST | WARN |
| `dependency_cycles` | No circular imports | BLOCK |

## Scanner Modes

- **BLOCK** — Failure prevents deployment. UCE exits non-zero.
- **WARN** — Failure is logged but doesn't block deployment.

## Adding a Scanner

Create a new file in `stateweave/compliance/scanners/`:

```python
from stateweave.compliance.scanners.base import BaseScanner, ScanResult

class MyScanner(BaseScanner):
    name = "my_scanner"
    mode = "BLOCK"

    def scan(self) -> ScanResult:
        # Check something...
        return ScanResult(passed=True, details="All good")
```

The scanner is auto-discovered by UCE.
