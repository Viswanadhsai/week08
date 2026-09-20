terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.117"
    }
  }
}

provider "azurerm" {
  features {}
}

data "azurerm_resource_group" "main" {
  name = "deakinuni"
}

resource "azurerm_storage_account" "task102d" {
  name                     = "viswa102ds226051707"
  resource_group_name      = data.azurerm_resource_group.main.name
  location                 = data.azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

output "resource_group_name" {
  value = data.azurerm_resource_group.main.name
}

output "storage_account_name" {
  value = azurerm_storage_account.task102d.name
}