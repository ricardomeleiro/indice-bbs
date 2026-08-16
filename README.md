# Índice BBS por Embarcação

Aplicação web para lançamento mensal de KPIs de BBS (Behavior Based Safety) por
embarcação/ROV, com dashboard, Pareto de falhas, evolução temporal, ranking anual
e heatmap. Substitui a planilha `Indice_BBS_por_Embarcacao_v10_ATUALIZADA.xlsx`.

## Publicação

- **URL**: `https://hub.c-innovation.com.br/bbs/`
- **Modelo**: subpath do Hub Authentik com SSO forward-auth
- **Servidor**: EC2 18.188.46.180 (mesmo host do Hub)

Consulte [CLAUDE.md](CLAUDE.md) para arquitetura, deploy passo a passo, papéis e
o script de importação do histórico.

## Fluxo curto

```
cp .env.example .env
docker compose up -d --build
docker cp file.xlsx indicebbs_app:/tmp/bbs.xlsx
docker exec -it indicebbs_app python import_xlsx.py /tmp/bbs.xlsx
```
