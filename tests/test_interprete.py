# tests/test_interprete.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.interprete import formatear_resumen, interpretar
from src.modelo import construir_modelo
from src.solver import ejecutar_solver
from tests.test_modelo import escenario_base


def resumen_de(esc):
    modelo = construir_modelo(esc)
    return interpretar(modelo, ejecutar_solver(modelo))


def test_cobertura_y_envios():
    # 100 unidades disponibles, 140 pedidas: A recibe 80 y B recibe 20
    r = resumen_de(escenario_base())
    assert r.estado == "Optimal"
    assert abs(r.cobertura_global - 100 / 140 * 100) < 1e-6
    assert abs(r.cobertura_por_zona["A"] - 100.0) < 1e-6
    assert abs(r.cobertura_por_zona["B"] - 100 / 3) < 1e-6
    assert abs(r.cobertura_por_tipo["Agua"] - 100 / 140 * 100) < 1e-6
    assert abs(r.enviado_por_centro["C1"]["Agua"] - 100) < 1e-6
    assert abs(r.recibido_por_zona["A"]["Agua"] - 80) < 1e-6
    assert abs(r.demanda_no_atendida_total - 40) < 1e-6


def test_rutas_costo_e_inventario():
    r = resumen_de(escenario_base())
    assert len(r.rutas_usadas) == 2
    assert abs(r.costo_total - 100) < 1e-6          # 100 unidades x costo 1
    assert abs(r.inventario_restante["C1"]["Agua"]) < 1e-6


def test_ruta_bloqueada_no_aparece():
    r = resumen_de(escenario_base(ruta_b=False))
    assert list(r.rutas_usadas) == [("C1", "A")]
    assert abs(r.inventario_restante["C1"]["Agua"] - 20) < 1e-6


def test_escenario_infactible():
    r = resumen_de(escenario_base(ruta_a=False))
    assert r.estado == "Infeasible"
    assert not r.tiene_solucion
    assert r.rutas_usadas == {}


if __name__ == "__main__":
    test_cobertura_y_envios()
    test_rutas_costo_e_inventario()
    test_ruta_bloqueada_no_aparece()
    test_escenario_infactible()
    print(formatear_resumen(resumen_de(escenario_base())))
    print("\nTodas las pruebas del intérprete pasaron")