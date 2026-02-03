from django.shortcuts import render
from .models import Wallet, WalletTransaction

# Userside
# -------------------------------------------
# Wallet Listing
def wallet_view(request):
    return render(request, 'user_side/profile/wallet/wallet.html')



# Admin Side
# -------------------------------------------
# Admin Wallet Management View
def AdminWalletListView(request):
    return render(request, 'admin_panel/wallet/wallet_management.html')