from dataclasses import dataclass, field


@dataclass
class Prioridad:
    nombre: str
    peso: float              # w[z] del modelo (Crítica 4, Alta 3, ...)
    critica: bool = False    # crit[z]: activa la atención mínima (R5)


@dataclass
class TipoAyuda:
    nombre: str
    indivisible: bool = False   # indiv[t]: True -> variable entera


@dataclass
class Centro:
    nombre: str
    capacidad_despacho: float                                # desp[c]
    activo: bool = True
    inventario: dict[str, float] = field(default_factory=dict)  # tipo -> inv[c,t]
    reserva: dict[str, float] = field(default_factory=dict)     # tipo -> res[c,t]


@dataclass
class Zona:
    nombre: str
    poblacion: int
    prioridad: str                                              # nombre de una Prioridad
    demanda: dict[str, float] = field(default_factory=dict)     # tipo -> dem[z,t]


@dataclass
class Ruta:
    origen: str                # nombre del centro
    destino: str               # nombre de la zona
    disponible: bool = True    # False = bloqueada (disp[c,z] = 0)
    costo: float = 0.0         # k[c,z] por unidad
    capacidad: float = 0.0     # capR[c,z]


@dataclass
class Escenario:
    centros: list[Centro] = field(default_factory=list)
    zonas: list[Zona] = field(default_factory=list)
    tipos: list[TipoAyuda] = field(default_factory=list)
    prioridades: list[Prioridad] = field(default_factory=list)
    rutas: list[Ruta] = field(default_factory=list)
    alfa: float = 0.3          # fracción mínima para zonas críticas (R5)

    # --- Utilidades que usará el constructor del modelo ---
    def prioridad_de(self, zona: Zona) -> Prioridad:
        return next(p for p in self.prioridades if p.nombre == zona.prioridad)

    def ruta_entre(self, centro: str, zona: str) -> Ruta | None:
        for r in self.rutas:
            if r.origen == centro and r.destino == zona:
                return r
        return None