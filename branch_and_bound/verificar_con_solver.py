# Comprueba con el software el análisis manual de Branch and Bound (analisis_manual.md)
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.dominio import Centro, Escenario, Prioridad, Ruta, TipoAyuda, Zona
from src.modelo import construir_modelo
from src.solver import ejecutar_solver


def instancia(indivisible):
    """1 centro, 1 tipo de ayuda (Kit) y 3 zonas. Costos de transporte en 0."""
    return Escenario(
        centros=[Centro("C1", capacidad_despacho=6, inventario={"Kit": 6})],
        zonas=[
            Zona("Z1", 0, "Critica", {"Kit": 15}),
            Zona("Z2", 0, "Alta", {"Kit": 2}),
            Zona("Z3", 0, "Media", {"Kit": 2}),
        ],
        tipos=[TipoAyuda("Kit", indivisible)],
        prioridades=[
            Prioridad("Critica", 4, True),
            Prioridad("Alta", 3),
            Prioridad("Media", 2),
        ],
        rutas=[Ruta("C1", z, True, 0, 10) for z in ["Z1", "Z2", "Z3"]],
        alfa=0.3,
    )


def resolver_nodo(cambios):
    """Resuelve la relajación lineal agregando las cotas del nodo.
    cambios: lista de (zona, signo, valor), por ejemplo ("Z2", "<=", 1)."""
    modelo = construir_modelo(instancia(indivisible=False))
    for zona, signo, valor in cambios:
        x = modelo.x["C1", zona, "Kit"]
        modelo.problema += (x <= valor) if signo == "<=" else (x >= valor)
    return ejecutar_solver(modelo)


nodos = {
    "N0 (raiz)": [],
    "N1": [("Z2", "<=", 1)],
    "N2": [("Z2", ">=", 2)],
    "N3": [("Z2", "<=", 1), ("Z3", "<=", 0)],
    "N4": [("Z2", "<=", 1), ("Z3", ">=", 1)],
    "N5": [("Z2", "<=", 1), ("Z3", ">=", 1), ("Z2", "<=", 0)],
    "N6": [("Z2", "<=", 1), ("Z3", ">=", 1), ("Z2", ">=", 1)],
}

print("Relajacion lineal en cada nodo del arbol")
for nombre, cambios in nodos.items():
    s = resolver_nodo(cambios)
    if s.tiene_solucion:
        x = [s.valores_x["C1", z, "Kit"] for z in ["Z1", "Z2", "Z3"]]
        print(f"{nombre}: x = {[round(v, 4) for v in x]}  Z = {s.valor_objetivo:.4f}")
    else:
        print(f"{nombre}: {s.estado}")

print("\nSolucion entera del software")
modelo = construir_modelo(instancia(indivisible=True))
s = ejecutar_solver(modelo)
x = [s.valores_x["C1", z, "Kit"] for z in ["Z1", "Z2", "Z3"]]
print(f"x = {x}  Z = {s.valor_objetivo:.4f}")
print(f"variables: {s.num_variables}, restricciones: {s.num_restricciones}")