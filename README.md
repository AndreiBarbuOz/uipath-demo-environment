# UiPath Demo environment

Create the environment needed to run the UiPath demo VMs found here

## Installation and prerequisites

### Installation

```bash
az group deployment create --resource-group <rg-name> --template-file lab/azuredeploy.json --name <deployment-name> --parameters lab/azuredeploy.parameters.json
```

After deployment, get the output values using:
```bash
az group deployment show --name <deployment-name> --resource-group <rg-name> --query properties.outputs -o json
```

Use these values to fill in the parameters required in `vm/azuredeploy.parameters.json`

### Create VM

```bash
az group deployment create --resource-group <rg-name> --template-file lab/azuredeploy.json --name <deployment-name> --parameters lab/azuredeploy.parameters.json
```

