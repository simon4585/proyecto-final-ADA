# Análisis reducido de Branch and Bound (§14)

## 1. Instancia reducida

1 centro, 1 tipo de ayuda indivisible (Kit) y 3 zonas. Costos de transporte en 0 (por eso `eps = 0`) y `alpha = 0.3`.

| Dato | Valor |
|---|---|
| Inventario y despacho de C1 | 6 y 6 |
| Z1 (Crítica, w = 4) | demanda 15 |
| Z2 (Alta, w = 3) | demanda 2 |
| Z3 (Media, w = 2) | demanda 2 |
| Rutas C1 → Zi | disponibles, capacidad 10 |

## 2. Formulación del problema entero

Como `n[z] = dem[z] − x[z]` (R4), el modelo se escribe solo con `x1, x2, x3` (kits enviados a Z1, Z2, Z3):

```
min  Z = 4·(15 − x1)/15 + 3·(2 − x2)/2 + 2·(2 − x3)/2
       = 9 − ( (4/15)·x1 + (3/2)·x2 + 1·x3 )

s.a. x1 + x2 + x3 <= 6        (R1 inventario y R2 despacho)
     x1 <= 10, x2 <= 10, x3 <= 10   (R3 capacidad de ruta, no activa)
     x1 <= 15, x2 <= 2, x3 <= 2     (R4 con n >= 0: no enviar más que la demanda)
     x1 >= 0.3 · 15 = 4.5     (R5 atención mínima en la zona crítica)
     x1, x2, x3 enteras >= 0  (R6 y R7)
```

Minimizar Z equivale a maximizar `G = (4/15)·x1 + (3/2)·x2 + x3`, y `Z = 9 − G`.

## 3. Relajación lineal

Es el mismo problema sin la condición de que `x` sea entera (solo `x >= 0`).

**Cómo se resuelve a mano.** Es una mochila fraccionaria con un mínimo obligatorio: se reservan los 4.5 de R5 para x1 y el inventario sobrante se reparte en orden de aporte a G: Z2 (1.5), Z3 (1.0) y al final x1 (4/15).

## 4. Solución de la relajación (nodo raíz N0)

Se reservan 4.5 para x1 y sobran 1.5, que van a Z2 (cabe, su tope es 2):

```
x = (4.5, 1.5, 0)     G = 1.2 + 2.25 = 3.45     Z = 9 − 3.45 = 5.55
```

## 5. Variables fraccionarias y variable de ramificación

x1 = 4.5 y x2 = 1.5 son fraccionarias.

**Regla elegida:** ramificar sobre la variable fraccionaria con mayor aporte a la función objetivo (mayor `w/dem`). Entre x2 (1.5) y x1 (4/15) se elige **x2**. Se explora primero la rama `<=` (profundidad primero).

Ramas: **x2 <= 1** y **x2 >= 2**.

## 6. Árbol de Branch and Bound

```
N0  x=(4.5, 1.5, 0)   Z=5.55     fraccionaria -> ramificar x2
├─ N1: x2 <= 1   x=(4.5, 1, 0.5)   Z=5.80    fraccionaria -> ramificar x3
│   ├─ N3: x3 <= 0   x=(5, 1, 0)   Z=6.1667  ENTERA -> incumbente
│   └─ N4: x3 >= 1   x=(4.5, 0.5, 1)  Z=6.05  fraccionaria -> ramificar x2
│       ├─ N5: x2 <= 0   x=(4.5, 0, 1.5)  Z=6.30   PODA POR COTA
│       └─ N6: x2 >= 1   INFACTIBLE
└─ N2: x2 >= 2   INFACTIBLE
```

Orden de exploración: N0, N1, N3, N4, N5, N6, N2.

| Nodo | Cota agregada | Solución de la relajación | Z | Resultado |
|---|---|---|---|---|
| N0 | ninguna | (4.5, 1.5, 0) | 5.55 | ramificar x2 |
| N1 | x2 <= 1 | (4.5, 1, 0.5) | 5.80 | ramificar x3 |
| N3 | x3 <= 0 | (5, 1, 0) | 6.1667 | entera: incumbente |
| N4 | x3 >= 1 | (4.5, 0.5, 1) | 6.05 | ramificar x2 |
| N5 | x2 <= 0 | (4.5, 0, 1.5) | 6.30 | podado por cota |
| N6 | x2 >= 1 | no existe | n/a | podado por infactibilidad |
| N2 | x2 >= 2 | no existe | n/a | podado por infactibilidad |

**Cómo se resuelve cada nodo:**

- **N1** (x2 <= 1): x2 = 1, sobran 0.5 que van a x3.
- **N2** (x2 >= 2): x1 + x2 >= 4.5 + 2 = 6.5 > 6, no cabe en el inventario.
- **N3** (x3 <= 0): x2 = 1 y x3 = 0, el resto va a x1 (6 − 1 = 5).
- **N4** (x3 >= 1): se reservan 4.5 + 1 = 5.5, sobran 0.5 que van a x2 (aporte 1.5 > 4/15).
- **N5** (x2 <= 0): se reservan 5.5, sobran 0.5 que van a x3 (llega a 1.5).
- **N6** (x2 >= 1, junto con x2 <= 1): x2 = 1, y 4.5 + 1 + 1 = 6.5 > 6.

## 7. Cotas

El problema es de minimización:

- **Cota inferior (valor de la relajación):** la raíz da 5.55, ninguna solución entera puede ser mejor. Cada nodo hijo tiene una cota inferior mayor o igual que la de su padre.
- **Cota superior (mejor solución entera conocida, el incumbente):** aparece en N3 con **6.1667** (= 37/6).
- **Brecha inicial:** 6.1667 − 5.55 = 0.6167.

## 8. Podas

1. **Por infactibilidad (N2 y N6):** las cotas agregadas obligan a enviar más de los 6 kits del inventario, o a incumplir el mínimo de R5. No hay solución en esa rama.
2. **Por integralidad (N3):** la relajación ya es entera, así que es la mejor solución de esa rama. Se guarda como incumbente y la rama no se explora más.
3. **Por cota (N5):** su relajación vale 6.30 y no es entera, pero 6.30 >= 6.1667. Cualquier solución entera dentro de esa rama valdría al menos 6.30, así que no puede mejorar el incumbente.

Con N2, N3, N5 y N6 cerrados y sin nodos abiertos, el incumbente es el óptimo.

## 9. Comparación con el software

Se ejecutó `branch_and_bound/verificar_con_solver.py`, que resuelve la relajación de cada nodo con el mismo modelo del software y luego el problema entero completo.

| | Análisis manual | Software (HiGHS) |
|---|---|---|
| Solución entera | x = (5, 1, 0) | x = (5, 1, 0) |
| Valor objetivo Z | 37/6 = 6.1667 | 6.1667 |
| Relajaciones de N0, N1, N3, N4, N5 | ver tabla | coinciden en los cinco nodos |
| N2 y N6 | infactibles | infactibles |

Datos del modelo en el software: 6 variables y 9 restricciones. Cobertura global: 6/19 = 31.58 % (Z1 33.33 %, Z2 50 %, Z3 0 %).

**Observación.** HiGHS aplica su propia estrategia de ramificación y puede visitar los nodos en otro orden, pero ambos métodos llegan al mismo óptimo. La fracción 4.5 viene de R5 (0.3 × 15): es la restricción que hace fraccionaria la relajación.