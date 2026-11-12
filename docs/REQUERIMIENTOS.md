# Requerimientos del Sistema

## 1. Requerimientos Funcionales

### 1.1 Gestión de usuarios y accesos

1. El sistema deberá permitir la gestión (alta, baja y modificación) de usuarios. La baja será lógica: el usuario queda inactivo y no puede iniciar sesión, pero se conserva su historial.
2. El sistema deberá listar usuarios de cualquier rol, incluido el de Administrador, distinguiéndolos explícitamente del rol de Representante a nivel de sistema, con búsqueda por nombre o email y filtro por estado.
3. El sistema deberá gestionar representantes.
4. El sistema deberá listar representantes, distinguiéndolos explícitamente del rol de Cliente a nivel de sistema.
5. El sistema deberá contemplar un rol de Administrador, responsable de gestionar usuarios, categorías, tipos de producto y productos, y de consultar, solo en lectura, todos los tickets (RF 1.4.8).
6. El sistema deberá permitir al Administrador reactivar usuarios inactivos.
7. El sistema deberá permitir a cualquier usuario autenticado cambiar su propia contraseña, y al Administrador restablecer la de cualquier usuario sin conocer la anterior.
8. El sistema deberá permitir a un usuario autenticado consultar su propia identidad (nombre, email y rol).
9. El sistema deberá permitir al Representante listar los clientes activos, con su identificador y nombre únicamente, para elegir el cliente de un ticket.

### 1.2 Gestión de tipos de producto

1. El sistema deberá permitir la gestión (alta, baja y modificación) de tipos de producto.
2. El sistema deberá listar los tipos de producto con el fin de clasificarlos por rubro.
3. El sistema deberá permitir la gestión (alta, baja y modificación) de rubros (categorías).
4. El sistema deberá permitir buscar rubros y tipos de producto por nombre.

### 1.3 Gestión de productos

1. El sistema deberá permitir la gestión (alta, baja y modificación) de productos. La baja será lógica: el producto inactivo se conserva en los tickets existentes, pero no puede asociarse a tickets nuevos.
2. El sistema deberá permitir asociar tipos de producto a productos.
3. El sistema deberá permitir listar productos.
4. El sistema deberá permitir al Administrador reactivar productos inactivos.
5. El sistema deberá permitir buscar productos por nombre y filtrar el listado por estado, además de por categoría y tipo de producto.

### 1.4 Gestión del ciclo de vida del ticket

1. El sistema deberá permitir a los representantes telefónicos la creación de tickets al recibir una consulta de servicio de un cliente.
2. El sistema deberá asociar cada ticket al cliente sobre el cual trata la consulta.
3. El sistema deberá asociar automáticamente el ticket al representante que lo generó, estableciéndose como encargado de su resolución.
4. El sistema deberá gestionar el estado de cada ticket (por ejemplo: Nuevo, En Progreso, Cerrado), permitiendo tanto al cliente como al representante cerrar el ticket.
5. El sistema deberá permitir la reapertura de un ticket cerrado, reasignándolo automáticamente al mismo representante que lo gestionó previamente y devolviéndolo al estado En Progreso.
6. El sistema deberá permitir asociar productos a tickets.
7. El sistema deberá permitir al representante asignado quitar productos asociados a un ticket.
8. El sistema deberá permitir al Administrador listar todos los tickets y consultar el detalle de cualquiera, solo en lectura: no podrá crearlos ni modificarlos.
9. El sistema deberá permitir filtrar el listado de tickets por estado, cliente, representante (solo el Administrador) y texto, y ordenarlo por fecha de creación.
10. El sistema deberá permitir consultar el historial de cambios de estado de un ticket al cliente dueño, al representante asignado y al Administrador.

### 1.5 Gestión de hitos

1. El sistema deberá gestionar y asociar hitos de forma estructurada a un ticket específico.
2. El sistema deberá listar los hitos de un ticket de forma estrictamente cronológica, construyendo un hilo continuo de comunicación entre cliente y representante.
3. El sistema deberá permitir al Administrador listar los hitos de cualquier ticket, solo en lectura.

### 1.6 Gestión de notificaciones

1. El sistema deberá gestionar el envío de notificaciones basadas en los eventos del ticket.
2. El sistema deberá notificar al cliente automáticamente cuando el representante registre un nuevo hito o cambie el estado del ticket.
3. El sistema deberá notificar al representante asignado cuando el cliente responda en el ticket, lo reabra o lo cierre.

### 1.7 Interfaz web

1. El sistema deberá ofrecer una interfaz web para los tres roles (Representante, Administrador y Cliente), servida por la propia API.
2. El sistema deberá ofrecer al Representante una pantalla para gestionar los tickets que tiene asignados: listarlos con filtros, ver su detalle con hitos e historial de estados, crear tickets eligiendo cliente y productos activos, registrar hitos, cerrar, reabrir y asociar o quitar productos.
3. El sistema deberá ofrecer al Administrador pantallas para administrar usuarios (incluidas cuentas de Administrador), categorías, tipos de producto y productos, y para consultar todos los tickets en solo lectura.
4. El sistema deberá ofrecer al Cliente un panel para listar y ver sus propios tickets (hitos y estados), responder, cerrarlos y reabrirlos.
5. El sistema deberá permitir iniciar y cerrar sesión desde la interfaz, mostrar el acceso solo cuando hay sesión válida y permitir cambiar la contraseña propia.
6. El sistema deberá mostrar todos los textos de la interfaz en español neutro y traducir los errores de la API a mensajes comprensibles para la persona usuaria.

## 2. Requerimientos No Funcionales

1. El sistema deberá ser codificado estrictamente utilizando la práctica de Test-Driven Development (TDD), asegurando la fiabilidad técnica desde su concepción.
2. El sistema deberá gestionar la seguridad mediante un sistema de autenticación (login) robusto.
3. El sistema no deberá permitir la duplicación de usuarios en la base de datos, garantizando unicidad mediante email o identificador.
4. El sistema deberá garantizar la privacidad, asegurando que un cliente solo pueda visualizar e interactuar con sus propios tickets.
5. El sistema deberá impedir la modificación o eliminación de los hitos una vez registrados, para preservar la integridad del historial en caso de disputas.
6. El sistema deberá registrar qué usuario (cliente o representante) y en qué momento exacto realizó un cambio de estado en el ticket.
7. El sistema deberá documentar su API HTTP con una especificación OpenAPI y exponerla de forma navegable mediante Swagger UI.
8. El sistema deberá servir su interfaz web desde la misma API, como archivos estáticos HTML, JavaScript y CSS sin paso de compilación ni dependencias de ejecución, y autenticarla con la misma cookie de sesión.
9. El sistema deberá verificar con pruebas unitarias automatizadas de JavaScript la lógica de la interfaz que no depende del DOM, ejecutadas en la integración continua.
10. El sistema deberá permitir, de forma opcional y compatible hacia atrás, paginar los listados que pueden crecer.
