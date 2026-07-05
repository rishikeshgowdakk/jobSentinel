import re

# 1. Update api.py
with open('../src/api.py', 'r') as f:
    api_content = f.read()

# Remove the donation endpoint
donate_endpoint_pattern = r'class DonationRequest\(BaseModel\):.*?@app\.delete\("/api/resume"\)'
api_content = re.sub(donate_endpoint_pattern, '@app.delete("/api/resume")', api_content, flags=re.DOTALL)

with open('../src/api.py', 'w') as f:
    f.write(api_content)


# 2. Update App.jsx
with open('App.jsx', 'r') as f:
    app_content = f.read()

# Replace the Support Us button action
old_button = """              <button 
                onClick={() => setShowPaymentModal(true)}
                className="w-full mt-2 py-2 border border-slate-300 dark:border-slate-700 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-[9px] font-bold uppercase tracking-wider transition-all duration-300 hover:-translate-y-0.5 active:scale-95 cursor-pointer"
              >
                Support Us / Donate
              </button>"""

new_button = """              <a 
                href="https://github.com/sponsors" 
                target="_blank" 
                rel="noopener noreferrer"
                className="w-full mt-2 py-2 border border-slate-300 dark:border-slate-700 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-[9px] font-bold uppercase tracking-wider transition-all duration-300 hover:-translate-y-0.5 active:scale-95 cursor-pointer flex items-center justify-center gap-2"
              >
                <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path></svg>
                Sponsor on GitHub
              </a>"""

app_content = app_content.replace(old_button, new_button)

# Remove modal state variables
state_vars_pattern = r'  const \[showPaymentModal, setShowPaymentModal\] = useState\(false\);\n  const \[paymentUtr, setPaymentUtr\] = useState\(\'\'\);\n  const \[paymentError, setPaymentError\] = useState\(\'\'\);\n  const \[paymentVerifying, setPaymentVerifying\] = useState\(false\);\n'
app_content = re.sub(state_vars_pattern, '', app_content)

# Remove submitDonation function
submit_donation_pattern = r'  const submitDonation = async \(utr\) => \{.*?  \};\n'
app_content = re.sub(submit_donation_pattern, '', app_content, flags=re.DOTALL)

# Remove the Modal completely
modal_pattern = r'      \{\/\* Payment Verification Modal \(UPI Pay-In ₹1\) \*\/\}.*?      \{\/\* CV Paste Modal \*\/\}'
app_content = re.sub(modal_pattern, '      {/* CV Paste Modal */}', app_content, flags=re.DOTALL)

with open('App.jsx', 'w') as f:
    f.write(app_content)

print("Removed donation modal successfully.")
