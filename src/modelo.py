from dataclasses import dataclass

import pulp

from src.dominio import Escenario

@dataclass
class ModeloConstruido:
    problema: pulp.LpProblem
    x: dict            # (centro, zona, tipo) -> variable de envío
    n: dict            # (zona, tipo) -> variable de demanda no atendida
    escenario: Escenario

    @property
    def num_variables(self):
        return self.problema.numVariables()

    @property
    def num_restricciones(self):
        return self.problema.numConstraints()


def construir_modelo(esc: Escenario) -> ModeloConstruido:
    prob = pulp.LpProblem("ayudas_humanitarias", pulp.LpMinimize)

    centros = [c.nombre for c in esc.centros]
    zonas = [z.nombre for z in esc.zonas]
    tipos = [t.nombre for t in esc.tipos]

    # ----- Parámetros del modelo, guardados en diccionarios -----
    inv, reserva, desp = {}, {}, {}
    for c in esc.centros:
        desp[c.nombre] = c.capacidad_despacho
        for t in tipos:
            inv[c.nombre, t] = c.inventario.get(t, 0) if c.activo else 0
            reserva[c.nombre, t] = c.reserva.get(t, 0)

    dem = {}
    peso, critica = {}, {}
    for z in esc.zonas:
        p = esc.prioridad_de(z)
        peso[z.nombre] = p.peso
        critica[z.nombre] = p.critica
        for t in tipos:
            dem[z.nombre, t] = z.demanda.get(t, 0)

    indivisible = {t.nombre: t.indivisible for t in esc.tipos}

    # Una ruta bloqueada o que no existe tiene capacidad 0
    cap, costo = {}, {}
    for c in centros:
        for z in zonas:
            r = esc.ruta_entre(c, z)
            cap[c, z] = r.capacidad if (r and r.disponible) else 0
            costo[c, z] = r.costo if r else 0

    # Solo hay variables para los pares (zona, tipo) con demanda
    pares = [(z, t) for z in zonas for t in tipos if dem[z, t] > 0]

    # ----- Variables -----
    x = {}
    for c in centros:
        for z, t in pares:
            categoria = pulp.LpInteger if indivisible[t] else pulp.LpContinuous
            x[c, z, t] = prob.add_variable(f"x{len(x)}", 0, None, categoria)

    n = {}
    for z, t in pares:
        n[z, t] = prob.add_variable(f"n{len(n)}", 0, None, pulp.LpContinuous)

    # ----- Valor de eps: el costo solo desempata, nunca le gana a la cobertura -----
    costo_max = sum(costo[c, z] * min(inv[c, t], cap[c, z], dem[z, t]) for c, z, t in x)
    mejora_minima = min((peso[z] / dem[z, t] for z, t in pares), default=0)
    eps = 0.5 * mejora_minima / costo_max if costo_max > 0 else 0

    # ----- Función objetivo -----
    no_atendida = pulp.lpSum(peso[z] * n[z, t] / dem[z, t] for z, t in pares)
    costo_total = pulp.lpSum(costo[c, z] * x[c, z, t] for c, z, t in x)
    prob += no_atendida + eps * costo_total

    # ----- Restricciones -----
    for c in centros:
        # R1: inventario (dejando la reserva mínima)
        for t in tipos:
            enviado = pulp.lpSum(x[c, z, t] for z in zonas if (z, t) in n)
            prob += enviado <= max(0, inv[c, t] - reserva[c, t]), f"R1_inventario_{c}_{t}"

        # R2: capacidad de despacho del centro
        prob += pulp.lpSum(x[c, z, t] for z, t in pares) <= desp[c], f"R2_despacho_{c}"

        # R3: capacidad de la ruta (si está bloqueada vale 0)
        for z in zonas:
            por_ruta = pulp.lpSum(x[c, z, t] for t in tipos if (z, t) in n)
            prob += por_ruta <= cap[c, z], f"R3_ruta_{c}_{z}"

    for z, t in pares:
        atendido = pulp.lpSum(x[c, z, t] for c in centros)

        # R4: atendido + no atendido = demanda
        prob += atendido + n[z, t] == dem[z, t], f"R4_demanda_{z}_{t}"

        # R5: atención mínima en zonas críticas
        if critica[z]:
            prob += atendido >= esc.alfa * dem[z, t], f"R5_minimo_critico_{z}_{t}"

    # R6 (no negatividad) y R7 (enteras) están en la creación de las variables

    return ModeloConstruido(prob, x, n, esc)