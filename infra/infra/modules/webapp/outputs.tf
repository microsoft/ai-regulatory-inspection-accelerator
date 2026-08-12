output "webapp_id" {
  description = "ID of the chat UI web app"
  value       = azurerm_linux_web_app.chat.id
}

output "webapp_name" {
  description = "Name of the chat UI web app"
  value       = azurerm_linux_web_app.chat.name
}

output "webapp_default_hostname" {
  description = "Default hostname of the chat UI web app"
  value       = azurerm_linux_web_app.chat.default_hostname
}
