# arsante

Módulo Odoo (localización/vertical) para **Method** que gestiona trámites regulatorios ante el ISP (Instituto de Salud Pública, Chile): cosméticos, dispositivos médicos, desinfectantes y alimentos (UYD).

> ⚠️ **Refactorización en curso (rama `refactor/arsante-generico`).** Los 22 modelos de trámite hardcodeados se están sustituyendo por **un modelo genérico con campos definidos por el usuario**. Durante la transición conviven ambos: lo descrito en "Modelo genérico" es lo nuevo; lo descrito más abajo es el legado que se eliminará. Plan completo en `~/.claude/plans/en-el-modulo-arsante-*.md`.

## Modelo genérico (arquitectura nueva)

- **`arsante.registro`** (`models/registro.py`): un único modelo para todos los trámites. 21 campos duros comunes (`date`, `partner_id`, `estado`, `facturado`, `sale_order_id`…) + `legacy_model`/`legacy_id` para trazar el origen tras la migración.
- **`arsante.campo`** (`models/campo.py`): definición de campo por tipo de registro. Cada uno se materializa como un campo REAL (`ir.model.fields` con `state='manual'`, prefijo `x_arsante_`), por lo que es filtrable, agrupable y exportable. Las columnas se **comparten por código** entre tipos, así que un mismo `code` debe tener el mismo `ttype` en todos (lo garantiza `_check_coherencia_codigo`).
- **`arsante.campo.opcion`**: opciones de los campos `selection`.
- **`models/plantilla.py`**: motor de plantillas `{codigo}` que sustituye a los 20 `create_so()`. `{codigo|raw}` inserta el valor crudo (necesario para reproducir literalmente las líneas de venta históricas, que concatenaban el código del selection y no su etiqueta).

### Reglas que no son obvias

- La inyección de campos en las vistas se hace sobrescribiendo **`_get_view`** (no `get_view`, no `fields_view_get`, eliminado en 16). **Nunca** escribir un `x_arsante_*` en un `arch_db` almacenado: `ir.model.fields._prepare_update` bloquearía renombrar o borrar ese campo.
- La clave de contexto es **`arsante_tipo_registro_id`**, no `default_...`: el `viewService` del cliente descarta las claves `default_*` al cachear la vista y serviría el formulario de otro tipo.
- Los `ir.model.fields` dinámicos van **siempre con `required=False`**: la columna es común a todos los tipos, y un `NOT NULL` rompería los registros de los demás. La obligatoriedad se aplica en la vista y al crear la nota de venta.
- Para las opciones de un selection en runtime hay que usar el **ORM** (`ir.model.fields.selection.create`), no `_update_selection`: ese último inserta con SQL directo y no dispara `setup_models`, dejando el campo sin opciones en el registry.
- Crear campos **en lote**: cada `create` de `ir.model.fields` dispara un `setup_models` completo (1-3 s).

## Migración

`migrations/16.0.2.0.0/` (7 scripts, `pre-`/`post-`/`end-`). El manifest está en `version: 2.0.0`; **no bajarla**. `pre-10_snapshot` copia las tablas al esquema `arsante_backup` **antes** de que Odoo pueda borrarlas, y `post-60_verificar` aborta la transacción entera si los conteos no cuadran. `tools/reset_migracion.py` deshace la migración en bases `*_test` para poder repetirla.

## Legado (en eliminación)

Cada tipo de trámite es un modelo propio con su wizard y vistas, y todos se agregan en un registro consolidado (`arsante.all_record`) usado para dashboard y facturación.

## Dependencias
`base`, `account`, `sale`, `contacts`.

## Estructura por dominio

Los trámites siguen un patrón repetido: modelo en `models/`, wizard en `wizard/`, vista en `views/`. Dominios cubiertos:

- **Cosméticos**: `cda_cosmetico_dm`, `registro_cosmetico`, `inscripciones_cosmeticos`, `modificacion_cosmeticos`, `rectificaciones`, `renovaciones_cosmeticas`, `eximiciones_cosmeticos` (+ `eximiciones_cosmeticos_correo.py`), `exim_proceso_cosmeticos`, `registro_isp_exim_cosmeticos`.
- **Dispositivos médicos**: `registro_dispositivos_medicos`, `declaracion_dispositivos_medicos`, `dispositivos_medicos`, `rev_antecedentes_dm`.
- **Desinfectantes**: `registro_desinfectantes`, `modificaciones_desinfectantes`, `renovaciones_desinfectantes`.
- **Alimentos**: `cda_uyd_alimentos`, `uyd_alimentos`.
- **Otros**: `hds_hechas`, `inscripciones`, `registro_isp`, `marca`, `tipo_registro`, `tipo_servicio`.

## Modelos clave

- `arsante.tipo_registro` (`models/tipo_registro.py`): catálogo maestro de tipos de trámite (selection `tipo`), con contadores computados (facturados, cotizados, listos, etc.) usados en el dashboard.
- `arsante.all_record` (`models/all_record.py`): tabla consolidada de todos los registros de trámites, con `registro_id` apuntando al ID del registro específico según `tipo_registro_id`. Se actualiza vía `onchange` cruzado — al modificar campos comunes (`facturado`, `estado`, `documentacion`, etc.) se busca y sincroniza el registro origen por `tipo_registro_id.name`. **Si se agrega un nuevo tipo de trámite, hay que replicar este patrón de sincronización.**

## Integraciones con core Odoo

- `res_company`: flag `es_arsante` que activa comportamiento específico en `sale.order`.
- `sale_order`: agrega `tipo_registro_id`, `tipo_servicio_id`, `marca`, `fecha_pago` y un campo computado `tipo_serv_registro` que combina servicio/registro para mostrar en la nota de venta. Sobrescribe `_prepare_invoice`.
- `account_move`, `res_partner`: extensiones para reportes y datos del trámite.
- `report/`: reportes QWeb para `sale_order` y `account_move`.

## Dashboard

`views/dashboard.xml` + assets en `static/src/{js,css,xml}/tipo_registro_dashboard.*` (OWL). Consume los campos computados de `arsante.tipo_registro`.

## Seguridad

- `security/ir.model.access.csv` + `data/groups.xml`: grupos de acceso por rol.
- Revisar ACL al agregar un modelo nuevo — es fácil olvidar la línea correspondiente en el CSV.

## Automatización

- `data/cron.xml`: tareas programadas (revisar antes de asumir que algo se actualiza solo por acción de usuario).

## Convenciones observadas

- Los modelos no usan `_description`; mantener consistencia si se agregan nuevos.
- Los campos y strings están en español, coherente con el dominio (trámites ISP Chile).
- Los wizards siguen el patrón `<modelo>_wizard.py` + `.xml`, y son el punto de entrada normal para crear un trámite (en vez de crear el registro directo).
- Hay archivos basura de metadatos de descarga (`*:Zone.Identifier`) en `controllers/` — no tocar/no replicar, son residuos de Windows/Google Drive, no parte del módulo.
