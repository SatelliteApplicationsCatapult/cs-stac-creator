# Process to add a new sensor configuration

This folder contains two subdirectories which content must be copied under `tests/data`, for the case of `data_template`,
and `test/output` for the case of `output_template`.

The placeholders are marked between `<` and `>`.

## Recommended steps

- Create a new branch
- Copy both directories content to the mention folders.
- Add the new sensor's configuration to [config.json](../../src/sac_stac/config.json).
- Fill all template's placeholders with the correct information.
- Submit a PR
- Fix any mistake if there is any until all test pass.