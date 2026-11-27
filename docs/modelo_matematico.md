# Modelo matemático: distribución de ayudas humanitarias

## 1. Descripción breve

Dado un escenario de emergencia con centros de almacenamiento, zonas afectadas, tipos de ayuda y rutas, se decide cuánto enviar de cada tipo de ayuda desde cada centro hacia cada zona. El objetivo es maximizar la cobertura de las necesidades, dando mayor importancia a las zonas de mayor prioridad y usando el costo de transporte solo como criterio de desempate.

## 2. Conjuntos e índices

| Símbolo | Descripción |
|---|---|
| `C` | Conjunto de centros de almacenamiento, índice `c` |
| `Z` | Conjunto de zonas afectadas, índice `z` |
| `T` | Conjunto de tipos de ayuda, índice `t` |
| `D` | Pares `(z,t)` con demanda positiva: `D = {(z,t) : dem[z,t] > 0}` |

## 3. Parámetros

| Símbolo | Descripción |
|---|---|
| `inv[c,t]` | Inventario del centro `c` del tipo de ayuda `t` (0 si el centro está inactivo) |
| `desp[c]` | Capacidad máxima de despacho del centro `c` |
| `dem[z,t]` | Demanda de la zona `z` del tipo de ayuda `t` |
| `w[z]` | Peso de la prioridad de la zona `z` (por ejemplo: Crítica 4, Alta 3, Media 2, Baja 1) |
| `disp[c,z]` | 1 si existe ruta disponible (no bloqueada) entre `c` y `z`, 0 en otro caso |
| `capR[c,z]` | Capacidad máxima de transporte de la ruta `(c,z)` |
| `k[c,z]` | Costo de transporte por unidad enviada por la ruta `(c,z)` |
| `indiv[t]` | 1 si el tipo de ayuda `t` es indivisible, 0 si es divisible |
| `res[c,t]` | Reserva mínima de inventario que debe conservar el centro `c` del tipo `t` |
| `alpha` | Fracción mínima de la demanda que debe atenderse en zonas críticas (por ejemplo, 0.3) |
| `crit[z]` | 1 si la zona `z` es de prioridad crítica, 0 en otro caso |
| `eps` | Peso muy pequeño del costo frente a la cobertura (se calcula, ver sección 8) |

## 4. Variables de decisión

Solo se definen para los pares `(z,t) ∈ D`, es decir, aquellos con demanda positiva. Esto evita variables sin sentido y reduce el tamaño del modelo.

| Variable | Dominio | Significado |
|---|---|---|
| `x[c,z,t]` | `x >= 0`; entera si `indiv[t] = 1`, continua si `indiv[t] = 0` | Cantidad del tipo `t` enviada desde el centro `c` hacia la zona `z` |
| `n[z,t]` | `n >= 0`, continua | Demanda del tipo `t` de la zona `z` que queda sin atender |

## 5. Función objetivo

```
min  Σ_{(z,t)∈D}  w[z] · n[z,t] / dem[z,t]   +   eps · Σ_c Σ_{(z,t)∈D}  k[c,z] · x[c,z,t]
```

**Interpretación:**

- `n[z,t] / dem[z,t]` es la **fracción** de la demanda que queda sin cubrir. Se normaliza para que los tipos de ayuda con cantidades grandes (por ejemplo, litros de agua) no dominen sobre los de cantidades pequeñas (por ejemplo, kits).
- `w[z]` multiplica esa fracción: dejar sin cubrir una zona crítica cuesta más que dejar sin cubrir una zona de prioridad baja. Así, ante escasez, el modelo atiende primero a las zonas más prioritarias.
- El segundo término es el costo total de transporte. Con `eps` muy pequeño, solo interviene para elegir la opción más barata entre soluciones con la misma cobertura, y nunca sacrifica cobertura por ahorrar costo.

## 6. Restricciones

**R1. Inventario disponible (con reserva mínima)**

```
Σ_{z : (z,t)∈D} x[c,z,t]  <=  max(0, inv[c,t] − res[c,t])        para todo c ∈ C, t ∈ T
```

Un centro no puede enviar más de lo que tiene, y debe conservar su reserva mínima. Con `res = 0` se reduce a la restricción básica de inventario.

**R2. Capacidad de despacho del centro**

```
Σ_{(z,t)∈D} x[c,z,t]  <=  desp[c]        para todo c ∈ C
```

El total despachado por un centro, sumando todos los destinos y tipos, no supera su capacidad.

**R3. Capacidad de transporte de la ruta y ruta bloqueada**

```
Σ_{t : (z,t)∈D} x[c,z,t]  <=  capR[c,z] · disp[c,z]        para todo c ∈ C, z ∈ Z
```

Cada ruta transporta como máximo su capacidad. Si la ruta está bloqueada o no existe (`disp = 0`), el lado derecho es 0 y no se puede enviar nada por ella.

**R4. Balance de demanda (demanda parcialmente insatisfecha)**

```
Σ_c x[c,z,t]  +  n[z,t]  =  dem[z,t]        para todo (z,t) ∈ D
```

Lo atendido más lo no atendido es igual a la demanda. Como `n >= 0`, lo atendido nunca supera la demanda. Como `n` puede ser positivo, el modelo admite que los recursos sean insuficientes y determina qué parte queda sin cubrir.

**R5. Atención mínima en zonas críticas (restricción adicional)**

```
Σ_c x[c,z,t]  >=  alpha · dem[z,t]        para todo (z,t) ∈ D con crit[z] = 1
```

Garantiza que las zonas críticas reciban al menos una fracción `alpha` de lo que demandan, antes de que el modelo pueda concentrar recursos en otras zonas. Si los recursos totales no alcanzan para cumplirla, el modelo es infactible; el sistema debe informarlo al usuario (ver supuestos).

**R6. No negatividad**

```
x[c,z,t] >= 0,   n[z,t] >= 0
```

**R7. Integralidad de ayudas indivisibles**

```
x[c,z,t] ∈ Z+        si indiv[t] = 1
```

Las ayudas indivisibles (por ejemplo, kits completos) se envían en cantidades enteras.

**Prioridad (requisito 7 del enunciado):** está incorporada en la función objetivo mediante `w[z]`. **Múltiples tipos de ayuda (requisito 10):** el índice `t` aparece en todas las expresiones.

## 7. Tipo de modelo

Es un modelo de **programación lineal entera mixta (PLEM)**: la función objetivo y todas las restricciones son lineales, y hay variables enteras (`x` de ayudas indivisibles) junto con variables continuas (`x` de ayudas divisibles y `n`).

- Si todas las ayudas fueran divisibles, se reduce a programación lineal (PL).
- Si todas fueran indivisibles, `x` sería entera, pero `n` seguiría siendo continua, por lo que sigue siendo PLEM salvo que la demanda sea entera y `n` se declare también entera (en ese caso es PLE).

Como el sistema debe ser genérico y admitir ambos tipos de ayuda, el caso general es PLEM.

## 8. Calibración de `eps` y supuestos

**Cálculo de `eps`.** Para que el costo actúe solo como desempate:

```
costo_max = Σ_c Σ_{(z,t)∈D}  k[c,z] · min(inv[c,t], capR[c,z], dem[z,t])     (solo rutas con disp[c,z] = 1)

eps = 0.5 · min_{(z,t)∈D} ( w[z] / dem[z,t] )  /  costo_max
```

- `costo_max` es una cota superior del costo de transporte de cualquier solución.
- `min w[z]/dem[z,t]` es la menor mejora de la función objetivo al cubrir **una unidad** de demanda.
- Con ese valor, cubrir una unidad más siempre compensa más que cualquier ahorro posible de costo. Si `costo_max = 0`, se toma `eps = 0`.
- Para ayudas divisibles es una aproximación razonable, pues la mejora mínima real puede ser menor que una unidad.

**Supuestos.**

1. Todas las cantidades de ayuda se expresan en una **unidad de carga común** para poder sumarlas en las restricciones de despacho (R2) y de ruta (R3).
2. El costo de transporte es **proporcional** a la cantidad enviada y no depende del tipo de ayuda.
3. Un centro inactivo se modela con `inv[c,t] = 0` para todo `t`.
4. Una ruta inexistente se trata igual que una ruta bloqueada: `disp[c,z] = 0`.
5. Si `alpha` hace infactible el escenario (recursos insuficientes para el mínimo de zonas críticas), el sistema debe informarlo al usuario en lugar de fallar sin explicación.
6. Los pares `(z,t)` con `dem[z,t] = 0` no generan variables ni términos en la función objetivo.

## 9. Justificación de las decisiones de modelado

- **Normalizar por la demanda:** mide la cobertura relativa en vez de unidades absolutas, lo que evita que los tipos de ayuda con cantidades grandes dominen la decisión.
- **Ponderar por `w[z]`:** hace que la prioridad influya de forma directa y lineal, manteniendo el modelo lineal.
- **Variable `n` explícita:** permite representar demanda no atendida sin forzar la igualdad entre envíos y demanda, y entrega directamente el dato que pide el §12 del enunciado.
- **Costo con `eps`:** evita objetivos en competencia con pesos arbitrarios; la cobertura manda y el costo desempata.
- **Restricciones adicionales:** la reserva mínima representa que un centro conserva inventario ante nuevas emergencias, y la atención mínima crítica asegura un piso de atención a la población más vulnerable.