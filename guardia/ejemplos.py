"""
Mensajes de ejemplo para probar GuardIA.

Sirven para dos cosas:
    1. Que cualquier persona pueda probar la aplicación sin tener a mano un
       correo sospechoso real.
    2. Testear el prompt durante el desarrollo. Por eso la lista incluye
       también correos legítimos: una herramienta que marca todo como phishing
       no sirve, así que hay que medir tanto los aciertos como los falsos
       positivos.

Todos los datos son ficticios.
"""

EJEMPLOS = [
    {
        "nombre": "Banco: cuenta bloqueada (phishing clásico)",
        "esperado": "alto",
        "remitente": "Banco Nación <seguridad@bna-verificacion.com>",
        "asunto": "URGENTE: su cuenta será bloqueada en 24 horas",
        "enlaces": "http://bna-verificacion.com/validar-datos",
        "cuerpo": (
            "Estimado cliente:\n\n"
            "Hemos detectado un acceso irregular a su cuenta. Por su seguridad, "
            "su home banking será bloqueado en las próximas 24 horas si no valida "
            "su identidad.\n\n"
            "Ingrese al siguiente enlace y complete sus datos de usuario, clave y "
            "los 3 dígitos del dorso de su tarjeta para reactivar el servicio:\n"
            "http://bna-verificacion.com/validar-datos\n\n"
            "No responda este correo. Departamento de Seguridad."
        ),
    },
    {
        "nombre": "Proveedor: cambio de CBU (fraude de factura)",
        "esperado": "alto",
        "remitente": "Administración Insumos del Sur <administracion@insumosdeIsur.com>",
        "asunto": "Re: Factura B 0003-00012845 - Nuevos datos bancarios",
        "enlaces": "",
        "cuerpo": (
            "Hola, ¿cómo estás?\n\n"
            "Te escribo para avisarte que cambiamos de banco. A partir de este mes "
            "las transferencias van a la nueva cuenta:\n\n"
            "CBU: 0170099220000012345678\n"
            "Titular: Insumos del Sur SRL\n\n"
            "La factura de este mes vence mañana, así que te agradecería que hagas "
            "la transferencia hoy a la cuenta nueva y me mandes el comprobante.\n\n"
            "Cualquier cosa escribime a este mail, estoy con el teléfono roto.\n\n"
            "Saludos,\nMartín - Administración"
        ),
    },
    {
        "nombre": "Falso pedido del gerente (fraude del CEO)",
        "esperado": "alto",
        "remitente": "Dr. Fernández <direccion.clinica@gmail.com>",
        "asunto": "Necesito un favor - confidencial",
        "enlaces": "",
        "cuerpo": (
            "Buen día,\n\n"
            "Estoy en una reunión y no puedo atender llamadas. Necesito que compres "
            "4 tarjetas de regalo de 50.000 pesos cada una para un cierre con "
            "proveedores. Es urgente.\n\n"
            "Comprálas y mandame una foto de los códigos por acá. Te lo reintegro "
            "hoy mismo. Por favor no comentes esto con nadie del equipo hasta que "
            "cerremos el acuerdo.\n\n"
            "Gracias.\nDr. Fernández"
        ),
    },
    {
        "nombre": "Turno médico confirmado (correo legítimo)",
        "esperado": "bajo",
        "remitente": "Turnos Clínica Modelo <turnos@clinicamodelo.com.ar>",
        "asunto": "Confirmación de turno - Lunes 24/08 10:30",
        "enlaces": "https://www.clinicamodelo.com.ar/mis-turnos",
        "cuerpo": (
            "Hola Agustín:\n\n"
            "Te confirmamos tu turno con el Dr. Pérez (Clínica Médica) para el lunes "
            "24/08 a las 10:30 en la sede de Av. Rivadavia 1234.\n\n"
            "Te pedimos que llegues 15 minutos antes con tu DNI y credencial de la "
            "obra social. Si no podés asistir, podés reprogramarlo desde tu cuenta "
            "en nuestro sitio.\n\n"
            "Saludos,\nEquipo de Turnos - Clínica Modelo"
        ),
    },
    {
        "nombre": "Aviso de paquete retenido (smishing por SMS)",
        # Al probar el prompt lo clasificó como alto, y tiene razón: el enlace
        # no es el oficial y pide un pago. La expectativa inicial era "medio".
        "esperado": "alto",
        "remitente": "+54 9 11 5555-0142",
        "asunto": "",
        "enlaces": "https://correo-arg.entrega-pendiente.net/pago",
        "cuerpo": (
            "CORREO ARGENTINO: tu paquete NRO 884213 esta retenido en aduana por "
            "falta de pago de $2.450. Regulariza en las proximas 48hs para evitar "
            "la devolucion al remitente: https://correo-arg.entrega-pendiente.net/pago"
        ),
    },
]


def buscar_ejemplo(nombre):
    """Devuelve el ejemplo cuyo nombre coincide, o None si no existe.

    Args:
        nombre: nombre visible del ejemplo.

    Returns:
        dict | None: el ejemplo encontrado.
    """
    for ejemplo in EJEMPLOS:
        if ejemplo["nombre"] == nombre:
            return ejemplo
    return None
