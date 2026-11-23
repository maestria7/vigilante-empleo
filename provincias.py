# (nombre, código de comunidad, slug colegios.es, slug colejobs.es, nombre para Talent.com)
PROVINCIAS = [
    ("Almería", "AND", "almeria", "almeria", "Almería"), ("Cádiz", "AND", "cadiz", "cadiz", "Cádiz"),
    ("Córdoba", "AND", "cordoba", "cordoba", "Córdoba"), ("Granada", "AND", "granada", "granada", "Granada"),
    ("Huelva", "AND", "huelva", "huelva", "Huelva"), ("Jaén", "AND", "jaen", "jaen", "Jaén"),
    ("Málaga", "AND", "malaga", "malaga", "Málaga"), ("Sevilla", "AND", "sevilla", "sevilla", "Sevilla"),
    ("Huesca", "ARA", "huesca", "huesca", "Huesca"), ("Teruel", "ARA", "teruel", "teruel", "Teruel"),
    ("Zaragoza", "ARA", "zaragoza", "zaragoza", "Zaragoza"),
    ("Asturias", "AST", "asturias", "asturias", "Asturias"),
    ("Islas Baleares", "BAL", "islas-baleares", "illes-balears", "Islas Baleares"),
    ("Las Palmas", "CAN", "las-palmas", "palmas-las", "Las Palmas"),
    ("Santa Cruz de Tenerife", "CAN", "santa-cruz-de-tenerife", "santa-cruz-de-tenerife", "Santa Cruz de Tenerife"),
    ("Cantabria", "CNT", "cantabria", "cantabria", "Cantabria"),
    ("Ávila", "CYL", "avila", "avila", "Ávila"), ("Burgos", "CYL", "burgos", "burgos", "Burgos"),
    ("León", "CYL", "leon", "leon", "León"), ("Palencia", "CYL", "palencia", "palencia", "Palencia"),
    ("Salamanca", "CYL", "salamanca", "salamanca", "Salamanca"), ("Segovia", "CYL", "segovia", "segovia", "Segovia"),
    ("Soria", "CYL", "soria", "soria", "Soria"), ("Valladolid", "CYL", "valladolid", "valladolid", "Valladolid"),
    ("Zamora", "CYL", "zamora", "zamora", "Zamora"),
    ("Albacete", "CLM", "albacete", "albacete", "Albacete"), ("Ciudad Real", "CLM", "ciudad-real", "ciudad-real", "Ciudad Real"),
    ("Cuenca", "CLM", "cuenca", "cuenca", "Cuenca"), ("Guadalajara", "CLM", "guadalajara", "guadalajara", "Guadalajara"),
    ("Toledo", "CLM", "toledo", "toledo", "Toledo"),
    ("Barcelona", "CAT", "barcelona", "barcelona", "Barcelona"), ("Girona", "CAT", "girona", "girona", "Girona"),
    ("Lleida", "CAT", "lleida", "lleida", "Lleida"), ("Tarragona", "CAT", "tarragona", "tarragona", "Tarragona"),
    ("Alicante", "VAL", "alicante", "alicante", "Alicante"), ("Castellón", "VAL", "castellon", "castellon", "Castellón"),
    ("Valencia", "VAL", "valencia", "valencia", "Valencia"),
    ("Badajoz", "EXT", "badajoz", "badajoz", "Badajoz"), ("Cáceres", "EXT", "caceres", "caceres", "Cáceres"),
    ("A Coruña", "GAL", "a-coruna", "coruna-a", "A Coruña"), ("Lugo", "GAL", "lugo", "lugo", "Lugo"),
    ("Ourense", "GAL", "ourense", "ourense", "Ourense"), ("Pontevedra", "GAL", "pontevedra", "pontevedra", "Pontevedra"),
    ("Madrid", "MAD", "madrid", "madrid", "Madrid"),
    ("Murcia", "MUR", "murcia", "murcia", "Murcia"),
    ("Navarra", "NAV", "navarra", "navarra", "Navarra"),
    ("Álava", "PV", "alava", "alava", "Álava"), ("Guipúzcoa", "PV", "guipuzcoa", "gipuzkoa", "Guipúzcoa"),
    ("Vizcaya", "PV", "vizcaya", "bizkaia", "Vizcaya"),
    ("La Rioja", "RIO", "la-rioja", "rioja-la", "La Rioja"),
    ("Ceuta", "CEU", "ceuta", "ceuta", "Ceuta"), ("Melilla", "MEL", "melilla", "melilla", "Melilla"),
]

COMUNIDADES = {
    "AND": "Andalucía", "ARA": "Aragón", "AST": "Asturias", "BAL": "Islas Baleares", "CAN": "Canarias",
    "CNT": "Cantabria", "CYL": "Castilla y León", "CLM": "Castilla-La Mancha", "CAT": "Cataluña",
    "VAL": "Comunidad Valenciana", "EXT": "Extremadura", "GAL": "Galicia", "MAD": "Madrid", "MUR": "Murcia",
    "NAV": "Navarra", "PV": "País Vasco", "RIO": "La Rioja", "CEU": "Ceuta", "MEL": "Melilla",
}

# Para Jobsora (búsqueda por comunidad): código -> texto de la URL
JOBSORA_LUGAR = {
    "AND": "andalucia", "ARA": "aragon", "AST": "asturias", "BAL": "islas-baleares", "CAN": "canarias",
    "CNT": "cantabria", "CYL": "castilla-y-leon", "CLM": "castilla-la-mancha", "CAT": "cataluna",
    "VAL": "comunidad-valenciana", "EXT": "extremadura", "GAL": "galicia", "MAD": "madrid",
    "MUR": "region-de-murcia", "NAV": "navarra", "PV": "pais-vasco", "RIO": "la-rioja",
}

# Palabras extra para deducir la comunidad a partir de un texto (ciudades grandes y nombres alternativos)
EXTRA_LUGARES = {
    "AND": ["andaluc", "marbella", "jerez", "algeciras", "dos hermanas", "estepona", "motril", "almuñécar", "benalmádena", "fuengirola", "torremolinos", "alcalá de guadaíra", "roquetas"],
    "ARA": ["aragón", "aragon"], "AST": ["gijón", "gijon", "oviedo", "avilés", "aviles"], "BAL": ["mallorca", "palma de", "ibiza", "menorca", "baleares", "balears"],
    "CAN": ["canarias", "tenerife", "gran canaria", "lanzarote", "fuerteventura"], "CNT": ["santander", "torrelavega"],
    "CYL": ["castilla y león", "castilla y leon", "ponferrada"], "CLM": ["castilla-la mancha", "castilla la mancha", "talavera", "albacete", "puertollano", "alcázar de san juan"],
    "CAT": ["cataluña", "catalunya", "sabadell", "terrassa", "badalona", "hospitalet", "mataró", "reus"], "VAL": ["comunidad valenciana", "valència", "elche", "gandia", "torrevieja", "benidorm", "orihuela"],
    "EXT": ["extremadura", "mérida", "merida", "plasencia"], "GAL": ["galicia", "vigo", "santiago de compostela", "ferrol", "coruña", "corunha"],
    "MAD": ["comunidad de madrid", "getafe", "alcalá de henares", "móstoles", "mostoles", "fuenlabrada", "leganés", "leganes", "alcorcón", "alcorcon", "pozuelo", "majadahonda", "las rozas", "torrejón", "alcobendas", "san sebastián de los reyes", "boadilla", "parla", "rivas", "collado villalba", "aranjuez", "tres cantos", "pinto", "valdemoro", "humanes", "coslada", "arganda"],
    "MUR": ["región de murcia", "region de murcia", "cartagena", "lorca", "molina de segura", "cabezo de torres", "yecla", "totana", "alcantarilla", "los belones", "san javier"],
    "NAV": ["pamplona", "navarra"], "PV": ["país vasco", "pais vasco", "euskadi", "bilbao", "vitoria", "san sebastián", "donostia", "getxo", "barakaldo"],
    "RIO": ["logroño", "rioja"], "CEU": [], "MEL": [],
}
