from typing import List
from sqlalchemy.orm.session import Session
from app.core.services import vector_store
from app.modules.tenderiq.db.schema import Tender

# TODO: Implement the following function as per requirements
def analyze_tender(db: Session, tdr: str):
    """
    # Description
    Analyze a tender by its tender ref number (Eg. "51655667"). On "tenders" table, it maps to "tender_ref_number" column.
    On "scraped_tenders" table, it maps to "tender_id_str" column.

    # Arguments
    - db: Session
    - tdr: str

    # Returns
    - None

    # Logical details
    1. Get all the details of a tender from both the "tenders" and "scraped_tenders" tables.
    2. Get a list of all the files associated with this tender (tender_documents)
    3. Download files to temporary storage
    4. Extract text from all files
    5. Vectorize and Embed
    6. Add to vector database (use vector_store)
    7. Do some LLM magic in order to fill up the "tender_analysis" table
        - Custom prompts required for every field of JSON data columns

    # Metadata
    - Expected completion time: 1 hour for steps 1-6, 2 hours for step 7

    """
    pass

def get_wishlisted_tenders(db: Session, tdr: str) -> List[Tender]:
    wishlisted = db.query(Tender).filter(Tender.is_wishlisted == True).all()
    return wishlisted
