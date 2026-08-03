# Network Radio Server Tests

Run the suite with:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

The tests validate:

- the manifest loads as YAML
- the new `network-radio-server.target` flag is present
- deploy/render wiring includes the new target
- the generated target unit includes the expected services
