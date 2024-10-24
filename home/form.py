# forms.py
from django import forms
from .models import SurveyResponse  # Import the SurveyResponse model

class SurveyForm(forms.ModelForm):
    class Meta:
        model = SurveyResponse
        fields = [
            'money_mission',
            'risk_tolerance',
            'market_fluctuations',
            'money_mojo',
            'debt_load',
            'emergency_fund',
            'investment_horizon',
            'investment_portfolio',
            'liquidity_needs',
            'tax_considerations',
            'stock_wizardry',
            'ethical_investing',
            'life_stage',
            'risk_parity',
        ]
