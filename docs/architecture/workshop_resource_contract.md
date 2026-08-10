# Workshop Resource Contract

## Purpose

A Workshop declares its own packages, models, capabilities and download sources. NaChance Core does not hard-code Workshop-specific model names or URLs.

## Resource lifecycle

```text
Workshop discovery
    -> read manifest/model registry/source registry
    -> resolve required resources
    -> provision missing resources
    -> verify files
    -> create/load Workshop engine
```

The engine must not be expected to download a required weight after it has already been initialized. Missing resources may disable only the affected optional capability; required resources should be reported explicitly.

## Runtime weight ownership

Workshop metadata declares the resource requirement. The physical runtime cache is owned by NaChance Core under `weights/`. This keeps the provisioner and Workshop engines on the same path and avoids downloading a model into one directory while the engine looks in another.

## Workshop independence

A Workshop must not call another Workshop directly. Connections between Workshop inputs and outputs are owned by NaChance Core pipelines/exchange.
