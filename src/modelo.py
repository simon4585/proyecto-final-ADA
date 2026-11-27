from dataclasses import dataclass

import pulp

from src.dominio import Escenario


@dataclass
class ModeloConstruido:
    """Resultado de construir el modelo: lo que necesita el solver y el intérprete."""
    problema: pulp.LpProblem
    x: dict            # (centro, zona, tipo) -> variable de envío
    n: dict            # (zona, tipo) -> variable de demanda no atendida
    eps: float         # peso del costo en la función objetivo
    escenario: Escenario

    @property
    def num_variables(self) -> int:
        return len(self.problema.variables())

    @property
    def num_restricciones(self) -> int:
        return len(self.problema.constraints)


def construir_modelo(esc: Escenario) -> ModeloConstruido:
    prob = pulp.LpProblem("Distribucion_Ayudas_Humanitarias", pulp.LpMinimize)

    # ---------- Parámetros (se leen del escenario) ----------
    def inv(c, t):
        return c.inventario.get(t.nombre, 0) if c.activo else 0

    def reserva(c, t):
        return c.reserva.get(t.nombre, 0)

    def dem(z, t):
        return z.demanda.get(t.nombre, 0)

    def ruta_disponible(c, z):
        r = esc.ruta_entre(c.nombre, z.nombre)
        return r is not None and r.disponible

    def cap_ruta(c, z):
        r = esc.ruta_entre(c.nombre, z.nombre)
        return r.capacidad if r is not None else 0

    def costo(c, z):
        r = esc.ruta_entre(c.nombre, z.nombre)
        return r.costo if r is not None else 0

    # ---------- Variables de decisión ----------
    # x[c,z,t]: solo se crean para pares (z,t) con demanda > 0
    x = {}
    for ci, c in enumerate(esc.centros):
        for zi, z in enumerate(esc.zonas):
            for ti, t in enumerate(esc.tipos):
                if dem(z, t) <= 0:
                    continue
                categoria = pulp.LpInteger if t.indivisible else pulp.LpContinuous
                x[(c.nombre, z.nombre, t.nombre)] = pulp.LpVariable(
                    f"x_{ci}_{zi}_{ti}", lowBound=0, cat=categoria
                )

    # n[z,t]: demanda no atendida
    n = {}
    for zi, z in enumerate(esc.zonas):
        for ti, t in enumerate(esc.tipos):
            if dem(z, t) > 0:
                n[(z.nombre, t.nombre)] = pulp.LpVariable(
                    f"n_{zi}_{ti}", lowBound=0, cat=pulp.LpContinuous
                )

    # ---------- Calibración de eps ----------
    # Cota superior del costo total y menor mejora de cobertura por una unidad
    costo_max = 0.0
    for c in esc.centros:
        for z in esc.zonas:
            for t in esc.tipos:
                if dem(z, t) > 0 and ruta_disponible(c, z):
                    ub = min(inv(c, t), cap_ruta(c, z), dem(z, t))
                    costo_max += costo(c, z) * ub

    mejoras = [
        esc.prioridad_de(z).peso / dem(z, t)
        for z in esc.zonas for t in esc.tipos if dem(z, t) > 0
    ]
    eps = 0.5 * min(mejoras) / costo_max if costo_max > 0 and mejoras else 0.0

    # ---------- Función objetivo ----------
    no_atendida_ponderada = pulp.lpSum(
        esc.prioridad_de(z).peso * n[(z.nombre, t.nombre)] / dem(z, t)
        for z in esc.zonas for t in esc.tipos if dem(z, t) > 0
    )
    costo_total = pulp.lpSum(
        costo(c, z) * x[(c.nombre, z.nombre, t.nombre)]
        for c in esc.centros for z in esc.zonas for t in esc.tipos
        if dem(z, t) > 0
    )
    prob += no_atendida_ponderada + eps * costo_total, "Objetivo"

    # ---------- Restricciones ----------
    for ci, c in enumerate(esc.centros):
        # R1. Inventario disponible menos reserva mínima
        for ti, t in enumerate(esc.tipos):
            enviado = pulp.lpSum(
                x[(c.nombre, z.nombre, t.nombre)]
                for z in esc.zonas if dem(z, t) > 0
            )
            prob += enviado <= max(0, inv(c, t) - reserva(c, t)), f"R1_inventario_{ci}_{ti}"

        # R2. Capacidad de despacho del centro
        despachado = pulp.lpSum(
            x[(c.nombre, z.nombre, t.nombre)]
            for z in esc.zonas for t in esc.tipos if dem(z, t) > 0
        )
        prob += despachado <= c.capacidad_despacho, f"R2_despacho_{ci}"

        # R3. Capacidad de la ruta (si está bloqueada o no existe, el límite es 0)
        for zi, z in enumerate(esc.zonas):
            por_ruta = pulp.lpSum(
                x[(c.nombre, z.nombre, t.nombre)]
                for t in esc.tipos if dem(z, t) > 0
            )
            limite = cap_ruta(c, z) if ruta_disponible(c, z) else 0
            prob += por_ruta <= limite, f"R3_ruta_{ci}_{zi}"

    for zi, z in enumerate(esc.zonas):
        pr = esc.prioridad_de(z)
        for ti, t in enumerate(esc.tipos):
            if dem(z, t) <= 0:
                continue
            atendido = pulp.lpSum(x[(c.nombre, z.nombre, t.nombre)] for c in esc.centros)

            # R4. Balance de demanda: atendido + no atendido = demanda
            prob += atendido + n[(z.nombre, t.nombre)] == dem(z, t), f"R4_balance_{zi}_{ti}"

            # R5. Atención mínima en zonas críticas
            if pr.critica:
                prob += atendido >= esc.alfa * dem(z, t), f"R5_minimo_critico_{zi}_{ti}"

    # R6 (no negatividad) y R7 (integralidad) van en la definición de las variables

    return ModeloConstruido(problema=prob, x=x, n=n, eps=eps, escenario=esc)