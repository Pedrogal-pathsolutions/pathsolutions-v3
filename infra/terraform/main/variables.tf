variable "alert_email" {
  description = "Destination of budget and monitoring alerts. Set in terraform.tfvars, which stays out of git."
  type        = string
  sensitive   = true
}
