"""
CMG Account Index — Deterministic CSV Loader & Normalized Index

Loads CMG_Account.csv into an in-memory index keyed by normalized name variants.
Each account produces index entries from: Account Name, Artist Name, Company Name, Legal Name.

Normalization: NFKC → lowercase → strip punctuation → collapse whitespace.
Index is built once at import/startup and is immutable thereafter.
"""
import csv
import logging
import re
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)

_CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "CMG_Account.csv"

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_MULTI_WS_RE = re.compile(r"\s+")

_NAME_FIELDS = [
    "Account Name",
    "Artist Name (pka or dba)",
    "Company Name",
    "Legal Name",
]


def normalize(text):
    if not text:
        return ""
    s = unicodedata.normalize("NFKC", str(text))
    s = s.lower()
    s = _PUNCT_RE.sub(" ", s)
    s = _MULTI_WS_RE.sub(" ", s).strip()
    return s


def tokenize(text):
    return tuple(sorted(set(normalize(text).split())))


class AccountRecord:
    __slots__ = (
        "account_name", "type", "id_18", "account_id", "le_id",
        "artist_name", "company_name", "legal_name",
        "contact_first", "contact_last",
        "normalized_names", "token_sets",
    )

    def __init__(self, row):
        self.account_name = (row.get("Account Name") or "").strip()
        self.type = (row.get("Type") or "").strip()
        self.id_18 = (row.get("18 Digit ID") or "").strip()
        self.account_id = (row.get("Account ID") or "").strip()
        self.le_id = (row.get("LE ID") or "").strip()
        self.artist_name = (row.get("Artist Name (pka or dba)") or "").strip()
        self.company_name = (row.get("Company Name") or "").strip()
        self.legal_name = (row.get("Legal Name") or "").strip()
        self.contact_first = (row.get("Primary Contact First Name") or "").strip()
        self.contact_last = (row.get("Primary Contact Last Name") or "").strip()

        raw_names = set()
        for field in _NAME_FIELDS:
            val = (row.get(field) or "").strip()
            if val:
                raw_names.add(val)

        self.normalized_names = tuple(sorted({normalize(n) for n in raw_names if normalize(n)}))
        self.token_sets = tuple(sorted({tokenize(n) for n in raw_names if normalize(n)}))

    @property
    def display_name(self):
        return self.account_name or self.artist_name or self.company_name or self.legal_name or self.account_id

    def to_candidate_dict(self):
        return {
            "account_name": self.account_name,
            "type": self.type,
            "account_id": self.account_id,
            "id_18": self.id_18,
            "le_id": self.le_id,
            "artist_name": self.artist_name,
            "company_name": self.company_name,
            "legal_name": self.legal_name,
        }


class AccountIndex:
    def __init__(self):
        self._records = []
        self._exact_map = {}
        self._loaded = False

    @property
    def loaded(self):
        return self._loaded

    @property
    def record_count(self):
        return len(self._records)

    def load(self, csv_path=None):
        path = Path(csv_path) if csv_path else _CSV_PATH
        if not path.exists():
            logger.warning("[ACCOUNT_INDEX] CSV not found: %s", path)
            return False

        records = []
        exact_map = {}

        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rec = AccountRecord(row)
                idx = len(records)
                records.append(rec)
                for norm_name in rec.normalized_names:
                    if norm_name not in exact_map:
                        exact_map[norm_name] = []
                    exact_map[norm_name].append(idx)

        self._records = records
        self._exact_map = exact_map
        self._loaded = True
        logger.info("[ACCOUNT_INDEX] Loaded %d accounts, %d index entries", len(records), len(exact_map))
        return True

    def exact_lookup(self, query):
        norm = normalize(query)
        if not norm:
            return []
        indices = self._exact_map.get(norm, [])
        return [self._records[i] for i in indices]

    def all_records(self):
        return self._records

    def get_exact_map(self):
        return self._exact_map


_global_index = AccountIndex()


def get_index():
    if not _global_index.loaded:
        _global_index.load()
    return _global_index


def ensure_loaded(csv_path=None):
    if not _global_index.loaded:
        return _global_index.load(csv_path)
    return True
