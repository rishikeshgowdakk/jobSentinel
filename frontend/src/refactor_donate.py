import re

with open('App.jsx', 'r') as f:
    content = f.read()

# 1. Replace the submit flow
old_submit_flow = """  const completePaymentAndSubmit = async (utr) => {
    const cleanUtr = utr.trim();
    if (cleanUtr) {
      if (!(/^\d{12}$/.test(cleanUtr) || cleanUtr === "TEST12345678")) {
        setPaymentError('Invalid UTR format. UTR must be exactly 12 digits if provided.');
        return;
      }
    }

    setPaymentVerifying(true);
    setPaymentError('');
    setIsError(false);

    if (pendingFile) {
      const formData = new FormData();
      formData.append('file', pendingFile);
      formData.append('utr', cleanUtr);

      setUploading(true);
      setMessage('Uploading and verifying payment...');

      try {
        const response = await axios.post(`${API_BASE}/resume/upload`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
        if (response.data.status === 'success') {
          setMessage(response.data.message);
          setPendingFile(null);
          setShowPaymentModal(false);
          loadAllData();
        } else {
          setPaymentError(response.data.message);
          setMessage(response.data.message);
          setIsError(true);
        }
      } catch (error) {
        console.error('Upload error details:', error);
        setPaymentError('Failed to verify payment or upload CV.');
        setMessage('Failed to upload resume.');
        setIsError(true);
      } finally {
        setUploading(false);
        setPaymentVerifying(false);
      }
    } else if (pendingPasteText) {
      setPasting(true);
      setMessage('Processing pasted CV and verifying payment...');

      try {
        const response = await axios.post(`${API_BASE}/resume/paste`, { 
          text: pendingPasteText,
          utr: cleanUtr
        });
        if (response.data.status === 'success') {
          setMessage(response.data.message);
          setPendingPasteText('');
          setPastedResumeText('');
          setShowPaymentModal(false);
          setShowPasteModal(false);
          loadAllData();
        } else {
          setPaymentError(response.data.message);
          setMessage(response.data.message);
          setIsError(true);
        }
      } catch (error) {
        setPaymentError('Failed to verify payment or process CV.');
        setMessage('Failed to connect to API server.');
        setIsError(true);
      } finally {
        setPasting(false);
        setPaymentVerifying(false);
      }
    } else {
      setPaymentVerifying(false);
      setPaymentError('No CV document loaded for evaluation.');
    }
  };"""

new_submit_flow = """  const submitDonation = async (utr) => {
    const cleanUtr = utr.trim();
    if (!cleanUtr) {
      setPaymentError('Please enter a 12-digit UTR.');
      return;
    }
    if (!/^\d{12}$/.test(cleanUtr)) {
      setPaymentError('Invalid UTR format. UTR must be exactly 12 digits.');
      return;
    }

    setPaymentVerifying(true);
    setPaymentError('');

    try {
      const response = await axios.post(`${API_BASE}/donate`, { utr: cleanUtr });
      if (response.data.status === 'success') {
        setShowPaymentModal(false);
        setPaymentUtr('');
        alert("Thank you for your generous donation!");
      } else {
        setPaymentError(response.data.message);
      }
    } catch (error) {
      setPaymentError('Failed to process donation.');
    } finally {
      setPaymentVerifying(false);
    }
  };"""

content = content.replace(old_submit_flow, new_submit_flow)

# 2. Replace upload handlers
old_upload = """  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setPendingFile(file);
    setPendingPasteText('');
    setPaymentUtr('');
    setPaymentError('');
    setShowPaymentModal(true);
    e.target.value = ''; // Reset input to allow selecting same file again
  };

  const handleResumePaste = async () => {
    if (!pastedResumeText.trim()) return;
    setPendingPasteText(pastedResumeText);
    setPendingFile(null);
    setPaymentUtr('');
    setPaymentError('');
    setShowPaymentModal(true);
  };"""

new_upload = """  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('utr', '');

    setUploading(true);
    setMessage('Uploading resume...');
    setIsError(false);

    try {
      const response = await axios.post(`${API_BASE}/resume/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      if (response.data.status === 'success') {
        setMessage(response.data.message);
        loadAllData();
      } else {
        setMessage(response.data.message);
        setIsError(true);
      }
    } catch (error) {
      console.error('Upload error details:', error);
      setMessage('Failed to upload resume.');
      setIsError(true);
    } finally {
      setUploading(false);
    }
    e.target.value = ''; 
  };

  const handleResumePaste = async () => {
    if (!pastedResumeText.trim()) return;
    
    setPasting(true);
    setMessage('Processing pasted CV...');
    setIsError(false);

    try {
      const response = await axios.post(`${API_BASE}/resume/paste`, { 
        text: pastedResumeText,
        utr: ''
      });
      if (response.data.status === 'success') {
        setMessage(response.data.message);
        setPastedResumeText('');
        setShowPasteModal(false);
        loadAllData();
      } else {
        setMessage(response.data.message);
        setIsError(true);
      }
    } catch (error) {
      setMessage('Failed to connect to API server.');
      setIsError(true);
    } finally {
      setPasting(false);
    }
  };"""

content = content.replace(old_upload, new_upload)

# 3. Update Modal Button
content = content.replace(
    'onClick={() => completePaymentAndSubmit(paymentUtr)}',
    'onClick={() => submitDonation(paymentUtr)}'
)
content = content.replace(
    "{paymentVerifying ? 'Processing...' : (paymentUtr.trim() ? 'Donate & Submit' : 'Skip & Submit')}",
    "{paymentVerifying ? 'Processing...' : 'Submit Donation'}"
)

# 4. Update Placeholder
content = content.replace(
    'placeholder="e.g. 627192837482 or TEST12345678"',
    'placeholder="e.g. 627192837482"'
)

# 5. Update Label
content = content.replace(
    'UPI Transaction UTR / Ref Number (Optional)',
    'UPI Transaction UTR / Ref Number (12 digits)'
)

# 6. Add persistent donate button under Pro Card
old_pro_card = """              <button 
                onClick={() => alert("JobSentinel Pro integration coming soon!")}
                className="w-full py-2.5 bg-black dark:bg-white hover:bg-neutral-800 dark:hover:bg-slate-200 text-white dark:text-slate-950 rounded-xl text-[9px] font-bold uppercase tracking-wider transition-all duration-300 shadow-md hover:-translate-y-1 hover:shadow-lg active:scale-95 cursor-pointer"
              >
                Elevate career with AI
              </button>
            </div>
          </div>
        </div>"""

new_pro_card = """              <button 
                onClick={() => alert("JobSentinel Pro integration coming soon!")}
                className="w-full py-2.5 bg-black dark:bg-white hover:bg-neutral-800 dark:hover:bg-slate-200 text-white dark:text-slate-950 rounded-xl text-[9px] font-bold uppercase tracking-wider transition-all duration-300 shadow-md hover:-translate-y-1 hover:shadow-lg active:scale-95 cursor-pointer"
              >
                Elevate career with AI
              </button>
              
              <button 
                onClick={() => setShowPaymentModal(true)}
                className="w-full mt-2 py-2 border border-slate-300 dark:border-slate-700 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-[9px] font-bold uppercase tracking-wider transition-all duration-300 hover:-translate-y-0.5 active:scale-95 cursor-pointer"
              >
                Support Us / Donate
              </button>
            </div>
          </div>
        </div>"""

content = content.replace(old_pro_card, new_pro_card)

# 7. Update Modal description 
old_modal_desc = """              <p className="text-xs text-slate-500 max-w-xs mx-auto">
                Scan the QR code to transfer a voluntary ₹1.00 donation to support autonomous matching. You can also skip this step!
              </p>"""

new_modal_desc = """              <p className="text-xs text-slate-500 max-w-xs mx-auto">
                Scan the QR code to transfer a voluntary ₹1.00 donation to support our servers. Thank you!
              </p>"""

content = content.replace(old_modal_desc, new_modal_desc)

with open('App.jsx', 'w') as f:
    f.write(content)

print("Done")
