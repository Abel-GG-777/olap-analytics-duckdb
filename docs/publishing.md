# Publicar en Dev.to

El artículo original en español está en `docs/devto.md`, escrito en primera persona singular. No está publicado: no se encontró una sesión accesible ni una credencial de Dev.to en esta ejecución.

1. Inicia sesión en [Dev.to](https://dev.to) y abre **Write a post**.
2. Usa el título, descripción y cuatro tags del bloque inicial de `docs/devto.md`.
3. Copia el cuerpo al editor Markdown. Si tu editor admite front matter, puedes pegar el archivo completo; revisa el preview antes de publicar.
4. Si ya verificaste Cloud Run, añade la URL real al README y sustituye los párrafos que describen el despliegue pendiente por lo efectivamente verificado. Incluye el enlace del run exitoso. El texto actual se puede publicar como laboratorio implementado con despliegue preparado; no describe una app pública activa.
5. Revisa tablas, bloques SQL y enlaces con **Preview**. Publica con **Publish** y guarda la URL resultante en este archivo.

Para que el agente publique en una continuación, habilita una sesión de Dev.to accesible o proporciona la clave mediante un gestor de secretos/variable de entorno `DEVTO_API_KEY`, sin incluirla en el repositorio ni pegarla en el artículo. Se debe comprobar la respuesta y la URL pública antes de dar la publicación por completada.
