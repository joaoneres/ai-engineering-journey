# Format of a pickup (dict):
#   id            (int)  locally generated identifier
#   customer_name (str)  customer name
#   address       (str)  pickup address
#   package_count (int)  number of packages (> 0)
#   priority      (str)  "low" | "medium" | "high"
#   status        (str)  "pending" | "in_transit" | "completed"

DATA_FILE = "pickups.json"
LOG_FILE = "filafacil.log"

PRIORITIES = ("low", "medium", "high")
STATUSES = ("pending", "in_transit", "completed")
INITIAL_STATUS = "pending"

PRIORITY_LABELS = {"low": "Baixa", "medium": "Média", "high": "Alta"}
STATUS_LABELS = {"pending": "Pendente", "in_transit": "Em rota", "completed": "Concluída"}
