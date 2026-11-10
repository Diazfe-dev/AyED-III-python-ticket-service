# Requerimientos del Sistema

## 1. Requerimientos Funcionales

### 1.1 Gestión de usuarios y accesos

1. El sistema deberá permitir la gestión (alta, baja y modificación) de usuarios. La baja será lógica: el usuario queda inactivo y no puede iniciar sesión, pero se conserva su historial.
2. El sistema deberá listar usuarios, distinguiéndolos explícitamente del rol de Representante a nivel de sistema.
3. El sistema deberá gestionar representantes.
4. El sistema deberá listar representantes, distinguiéndolos explícitamente del rol de Cliente a nivel de sistema.
5. El sistema deberá contemplar un rol de Administrador, responsable de gestionar usuarios, categorías, tipos de producto y productos.

### 1.2 Gestión de tipos de producto

1. El sistema deberá permitir la gestión (alta, baja y modificación) de tipos de producto.
2. El sistema deberá listar los tipos de producto con el fin de clasificarlos por rubro.
3. El sistema deberá permitir la gestión (alta, baja y modificación) de rubros (categorías).

### 1.3 Gestión de productos

1. El sistema deberá permitir la gestión (alta, baja y modificación) de productos. La baja será lógica: el producto inactivo se conserva en los tickets existentes, pero no puede asociarse a tickets nuevos.
2. El sistema deberá permitir asociar tipos de producto a productos.
3. El sistema deberá permitir listar productos.

### 1.4 Gestión del ciclo de vida del ticket

1. El sistema deberá permitir a los representantes telefónicos la creación de tickets al recibir una consulta de servicio de un cliente.
2. El sistema deberá asociar cada ticket al cliente sobre el cual trata la consulta.
3. El sistema deberá asociar automáticamente el ticket al representante que lo generó, estableciéndose como encargado de su resolución.
4. El sistema deberá gestionar el estado de cada ticket (por ejemplo: Nuevo, En Progreso, Cerrado), permitiendo tanto al cliente como al representante cerrar el ticket.
5. El sistema deberá permitir la reapertura de un ticket cerrado, reasignándolo automáticamente al mismo representante que lo gestionó previamente y devolviéndolo al estado En Progreso.
6. El sistema deberá permitir asociar productos a tickets.
7. El sistema deberá permitir al representante asignado quitar productos asociados a un ticket.

### 1.5 Gestión de hitos

1. El sistema deberá gestionar y asociar hitos de forma estructurada a un ticket específico.
2. El sistema deberá listar los hitos de un ticket de forma estrictamente cronológica, construyendo un hilo continuo de comunicación entre cliente y representante.

### 1.6 Gestión de notificaciones

1. El sistema deberá gestionar el envío de notificaciones basadas en los eventos del ticket.
2. El sistema deberá notificar al cliente automáticamente cuando el representante registre un nuevo hito o cambie el estado del ticket.
3. El sistema deberá notificar al representante asignado cuando el cliente responda en el ticket, lo reabra o lo cierre.

## 2. Requerimientos No Funcionales

1. El sistema deberá ser codificado estrictamente utilizando la práctica de Test-Driven Development (TDD), asegurando la fiabilidad técnica desde su concepción.
2. El sistema deberá gestionar la seguridad mediante un sistema de autenticación (login) robusto.
3. El sistema no deberá permitir la duplicación de usuarios en la base de datos, garantizando unicidad mediante email o identificador.
4. El sistema deberá garantizar la privacidad, asegurando que un cliente solo pueda visualizar e interactuar con sus propios tickets.
5. El sistema deberá impedir la modificación o eliminación de los hitos una vez registrados, para preservar la integridad del historial en caso de disputas.
6. El sistema deberá registrar qué usuario (cliente o representante) y en qué momento exacto realizó un cambio de estado en el ticket.
