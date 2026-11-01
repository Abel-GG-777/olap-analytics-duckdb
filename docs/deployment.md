# Despliegue en Google Cloud Run

## Estado y acceso necesario

El destino seleccionado es **Google Cloud**, sin componentes de AWS. El despliegue todavía necesita un proyecto GCP con facturación habilitada y una sesión autorizada. No se encontró `gcloud` ni una configuración local de GCP. No existe una URL pública verificada de esta aplicación.

Se necesita del propietario: un **project ID de GCP**, facturación activa y permiso para crear cuentas de servicio, configurar IAM/Workload Identity Federation, habilitar APIs y desplegar Cloud Run. No envíes claves privadas al chat. Puedes ejecutar la preparación en Cloud Shell con tu sesión y compartir los identificadores de recursos no secretos.

## Preparación una sola vez

Abre Google Cloud Shell dentro del proyecto autorizado y ejecuta:

```bash
git clone https://github.com/Abel-GG-777/olap-analytics-duckdb.git
cd olap-analytics-duckdb
export PROJECT_ID='TU_PROJECT_ID_REAL'
export REGION='us-central1'
bash scripts/setup-gcp.sh
```

Revisa antes los recursos que crea el script: tres cuentas de servicio (deploy, build y runtime), un pool OIDC y su proveedor. El runtime no recibe roles de proyecto. El builder recibe `roles/run.builder`. El deployer recibe `roles/run.admin`, `roles/run.sourceDeveloper`, `roles/serviceusage.serviceUsageConsumer` y `serviceAccountUser` sobre builder y runtime. `run.admin` permite establecer el acceso público de este servicio y es un permiso amplio dentro del proyecto: usa un proyecto dedicado para el laboratorio. Quien ejecuta el script requiere permisos administrativos, pero GitHub no recibe Owner ni Editor.

La condición OIDC restringe al ID numérico del propietario de GitHub, al repositorio exacto y a `refs/heads/main`. El script se puede reejecutar para completar recursos faltantes; si ya existe un proveedor con otra configuración, inspecciónalo y actualízalo explícitamente, pues el script conserva el existente. Las políticas de la organización pueden impedir invocación pública o federación; deben resolverse en la cuenta, no desactivarse desde el pipeline.

En GitHub → Settings → Secrets and variables → Actions → **Variables**, registra los seis valores impresos por el script:

| Variable | Contenido |
|---|---|
| `GCP_PROJECT_ID` | Project ID real |
| `GCP_REGION` | `us-central1` o región elegida |
| `GCP_WIF_PROVIDER` | Nombre completo `projects/NUM/locations/global/workloadIdentityPools/github-olap/providers/github` |
| `GCP_DEPLOY_SERVICE_ACCOUNT` | Email de `olap-deployer` |
| `GCP_BUILD_SERVICE_ACCOUNT` | Email de `olap-builder` |
| `GCP_RUNTIME_SERVICE_ACCOUNT` | Email de `olap-runtime` |

No son claves privadas. Crea el environment `production` en Settings → Environments; si agregas revisores obligatorios, cada despliegue esperará esa aprobación. Para despliegue automático sin intervención, no configures revisores obligatorios y limita las ramas permitidas a `main`.

## Flujo automatizado

1. Un PR ejecuta las verificaciones y prueba la imagen Docker; no recibe identidad GCP.
2. Un push a `main` ejecuta las mismas verificaciones.
3. Solo si pasan y existe `GCP_PROJECT_ID`, GitHub obtiene una identidad temporal OIDC. No se almacenan claves JSON.
4. `gcloud run deploy --source .` usa Cloud Build y Artifact Registry para construir y servir el Dockerfile en Cloud Run.
5. La base de datos se genera dentro de la imagen y se usa en modo de solo lectura. El servicio no requiere almacenamiento persistente.
6. El workflow obtiene `status.url`, verifica `/health`, un filtro analítico y la página principal. Publica la URL comprobada en el resumen de Actions. Si falla el smoke, el workflow falla; no revierte automáticamente la revisión ya desplegada.

Dispara el primer despliegue desde Actions → Verify and deploy OLAP → Run workflow, rama `main`, después de configurar las variables. Revisa ambos jobs: `verify` y `deploy`. Un job omitido no equivale a un despliegue exitoso.

## Configuración operacional

Un proceso por contenedor, 1 CPU, 1 GiB de memoria, concurrencia 8, mínimo 0 y máximo 2 instancias; timeout 60 segundos. No son resultados de pruebas de carga. El mínimo 0 habilita reducción a cero, con posible arranque en frío. Cloud Build, imágenes, logs y solicitudes pueden generar cargos; configura un presupuesto en tu proyecto. El límite de instancias no es un límite monetario.

Para comprobar manualmente desde Cloud Shell:

```bash
URL=$(gcloud run services describe olap-analytics-duckdb --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)')
python3 scripts/smoke.py "$URL"
```

Tras verificar, incorpora esa URL real al README y al artículo, y registra el enlace del run exitoso en `docs/verification.md`.

Si una revisión falla, inspecciona Cloud Run → Logs y el run de GitHub. Puedes revertir el código mediante un nuevo commit o dirigir tráfico a una revisión anterior sana desde Cloud Run. Para detener costos de ejecución, elimina el servicio desde la consola; las imágenes almacenadas y otros recursos pueden seguir generando costos hasta que los elimines.

## Fuentes oficiales consultadas

- [Despliegue desde código fuente](https://docs.cloud.google.com/run/docs/deploying-source-code)
- [Roles de Cloud Run](https://docs.cloud.google.com/run/docs/reference/iam/roles)
- [Federación para pipelines](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)
- [Acción oficial de autenticación](https://github.com/google-github-actions/auth)
