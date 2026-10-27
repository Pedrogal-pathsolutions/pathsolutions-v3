# Terraform da v3

- `bootstrap/`: grupo `rg-pathsol-v3` e a conta do estado remoto (`pathsoltfstatev3`). O próprio estado dele fica nessa conta, na chave `bootstrap.tfstate`.
- `main/`: o resto da v3, com estado na chave `main.tfstate`.

VM1, VM2, discos atuais e rede não entram aqui, salvo como `data`. Nunca `terraform import` nem `terraform destroy`.

## Como roda (decisão 4)

- O Terraform usa só o login do `az` do Pedro (`use_cli = true`, `use_msi = false` no provider e no backend), nunca a identidade gerenciada da VM1.
- O Claude escreve o código e roda `fmt`, `validate` e `plan -out`, com o login do Pedro ativo. O resumo do plano vai para o relatório da fase.
- O apply é do Pedro, num terminal SSH comum na VM1, com o Antigravity fechado e o plano salvo. No fim do dia de Terraform, `az logout`.

Em todo terminal:

```
export PATH=$HOME/.local/bin:$PATH CHECKPOINT_DISABLE=1
az account show --query id -o tsv   # bd87a1ca-e4f5-460b-9f12-c89e114293f1, senão pare
```

## Apply de um plano salvo

```
cd ~/pathsolutions-v3/infra/terraform/<bloco>
sha256sum <plano>.tfplan            # nome e hash no relatório da fase
terraform apply <plano>.tfplan
```

Se o plano estiver velho (o estado mudou depois dele), o Terraform recusa; nesse caso, pare e peça um plano novo.

## Primeiro apply do bootstrap e migração do estado

O primeiro plano do bootstrap foi feito com backend local (`backend_override.tf`, fora do git), porque a conta do estado ainda não existe. Logo depois do apply:

```
cd ~/pathsolutions-v3/infra/terraform/bootstrap
terraform apply bootstrap.tfplan
rm backend_override.tf
terraform init -migrate-state -force-copy -input=false
terraform state list                # os 5 recursos, lidos da conta nova
```

Se o `init` falhar com 403 (`AuthorizationPermissionMismatch`), o papel de dados ainda está propagando: espere de 2 a 5 minutos e repita o `init`.

## Variáveis do `main/`

O e-mail dos alertas fica em `main/terraform.tfvars` (`alert_email = "..."`), fora do git, e é `sensitive` no código. O arquivo `.tfplan` guarda o valor em texto claro: também fica fora do git.
