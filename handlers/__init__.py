from handlers.start import router as start_router
from handlers.buy import router as buy_router
from handlers.keys import router as keys_router
from handlers.support import router as support_router
from handlers.referral import router as referral_router
from handlers.guide import router as guide_router
from handlers.admin import router as admin_router

all_routers = [
    start_router,
    buy_router,
    keys_router,
    support_router,
    referral_router,
    guide_router,
    admin_router,
]