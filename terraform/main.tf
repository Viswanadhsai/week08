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

data "azurerm_resource_group" "week08" {
  name = "VISWA-RG08"
}

data "azurerm_container_registry" "acr" {
  name                = "viswa722acr08"
  resource_group_name = data.azurerm_resource_group.week08.name
}

data "azurerm_kubernetes_cluster" "aks" {
  name                = "viswa722aks08"
  resource_group_name = data.azurerm_resource_group.week08.name
}

data "azurerm_storage_account" "storage" {
  name                = "viswa722storage08"
  resource_group_name = data.azurerm_resource_group.week08.name
}

output "resource_group" {
  value = data.azurerm_resource_group.week08.name
}

output "acr_name" {
  value = data.azurerm_container_registry.acr.name
}

output "aks_name" {
  value = data.azurerm_kubernetes_cluster.aks.name
}

output "storage_name" {
  value = data.azurerm_storage_account.storage.name
}