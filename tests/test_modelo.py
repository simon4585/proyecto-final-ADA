from src.dominio import Centro, Escenario, Prioridad, Ruta, TipoAyuda, Zona
from src.modelo import construir_modelo
from src.solver import ejecutar_solver


def escenario_base(ruta_a=True, ruta_b=True) -> Escenario:
    """1 centro con 100 de agua; zona A crítica pide 80, zona B baja pide 60."""
    return Escenario(
        centros=[Centro(nombre="C1", capacidad_despacho=100, activo=True,
                        inventario={"Agua": 100})],
        zonas=[
            Zona(nombre="A", poblacion=500, prioridad="Crítica", demanda={"Agua": 80}),
            Zona(nombre="B", poblacion=300, prioridad="Baja", demanda={"Agua": 60}),
        ],
        tipos=[TipoAyuda(nombre="Agua", indivisible=False)],
        prioridades=[
            Prioridad(nombre="Crítica", peso=4, critica=True),
            Prioridad(nombre="Baja", peso=1, critica=False),
        ],
        rutas=[
            Ruta(origen="C1", destino="A", disponible=ruta_a, costo=1, capacidad=100),
            Ruta(origen="C1", destino="B", disponible=ruta_b, costo=1, capacidad=100),
        ],
        alfa=0.3,
    )


def resolver(esc):
    return ejecutar_solver(construir_modelo(esc))


def test_prioridad_ante_escasez():
    # Hay 100 y se piden 140: A (crítica) debe cubrirse completa y B recibe el resto
    sol = resolver(escenario_base())
    assert sol.estado == "Optimal"
    assert abs(sol.valores_x[("C1", "A", "Agua")] - 80) < 1e-6
    assert abs(sol.valores_x[("C1", "B", "Agua")] - 20) < 1e-6
    assert abs(sol.valores_n[("B", "Agua")] - 40) < 1e-6


def test_ruta_bloqueada():
    # Con la ruta a B bloqueada, B no recibe nada
    sol = resolver(escenario_base(ruta_b=False))
    assert sol.estado == "Optimal"
    assert sol.valores_x[("C1", "B", "Agua")] == 0
    assert abs(sol.valores_n[("B", "Agua")] - 60) < 1e-6


def test_infactible_por_minimo_critico():
    # Zona crítica sin ruta: no puede cumplir la atención mínima (R5)
    sol = resolver(escenario_base(ruta_a=False))
    assert sol.estado == "Infeasible"


if __name__ == "__main__":
    test_prioridad_ante_escasez()
    test_ruta_bloqueada()
    test_infactible_por_minimo_critico()
    print("Todas las pruebas pasaron")