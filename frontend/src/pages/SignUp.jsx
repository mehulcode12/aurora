import React, { useState } from 'react';
import { Shield, Mail, User, Briefcase, Building, FileText, CheckCircle, AlertCircle, ArrowRight, Upload, X,Lock, Eye, EyeOff} from 'lucide-react';
import { Link } from 'react-router-dom';
import { getOtp,verifyOtp } from '../services/authServices/authServices';
import { signUp } from '../services/authServices/authServices';
import { useNavigate } from 'react-router-dom';

export default function Signup() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: Email verification, 2: Full registration
  const [email, setEmail] = useState('projects.dev.om@gmail.com');
  const [otp, setOtp] = useState('');
  const [isOtpSent, setIsOtpSent] = useState(false);
  const [isSendingOtp, setIsSendingOtp] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(true);
  const [tempToken,setTempToken]= useState('');
  // Form fields
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    password:'',
    tempToken:'',
    position: '',
    companyName: '',
    companyManual: null
  });
  
  const [errors, setErrors] = useState({});

  // Handle OTP request
  const handleGetOtp = async () => {
    setErrors({});
    
    if (!email) {
      setErrors({ email: 'Email is required' });

      return;
    }
    
    if (!/\S+@\S+\.\S+/.test(email)) {
      setErrors({ email: 'Please enter a valid email address' });
      return;
    }
    
    // Simulate OTP sending
    setIsSendingOtp(true);
    const response = await getOtp(email);
    if(response?.data?.success !== true){
      setErrors({ email: 'Failed to send OTP. Please try again.' });
      setIsSendingOtp(false);
      return;
    }
    setIsSendingOtp(false);
    setIsOtpSent(true);
  };

  // Handle OTP verification
  const handleVerifyOtp = async () => {
    setErrors({});
    
    if (!otp) {
      setErrors({ otp: 'OTP is required' });
      return;
    }
    
    if (otp.length !== 6) {
      setErrors({ otp: 'OTP must be 6 digits' });
      return;
    }
    
    // Simulate OTP verification
    setIsVerifying(true);
    const response = await verifyOtp(email,otp);
    if(response?.status!==200){
    // if(response?.data?.success !== true){
      setErrors({ otp: 'Invalid OTP. Please try again.' });
      setIsVerifying(false);
    }
      setTempToken(response?.data?.temp_token);
      setIsVerifying(false);
      setStep(2);
  };

  // Handle file upload
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.type !== 'application/pdf') {
        setErrors({ ...errors, file: 'Please upload a PDF file' });
        return;
      }
      if (file.size > 10 * 1024 * 1024) { // 10MB limit
        setErrors({ ...errors, file: 'File size must be less than 10MB' });
        return;
      }
      setFormData({ ...formData, companyManual: file });
      setErrors({ ...errors, file: null });
    }
  };

  // Remove uploaded file
  const removeFile = () => {
    setFormData({ ...formData, companyManual: null });
  };

  // Handle form submission
  const handleSubmit = async () => {
    setErrors({});
    const newErrors = {};
    formData.tempToken=tempToken;
    // if(!tempToken) newErrors.tempToken = "Email not verified";
    if (!formData.firstName) newErrors.firstName = 'First name is required';
    if (!formData.lastName) newErrors.lastName = 'Last name is required';
    if (!formData.password) newErrors.password = 'Position is required';
    if (!formData.position) newErrors.position = 'Position is required';
    if (!formData.companyName) newErrors.companyName = 'Company name is required';
    if (!formData.companyManual) newErrors.file = 'Company manual is required';
    
    if (Object.keys(newErrors).length > 0) {
      console.log("ERRORS",newErrors);
      setErrors(newErrors);
      return;
    }
    
    // Simulate registration
    setIsSubmitting(true);
    const response = await signUp(email,formData);
    console.log(response);
    setTimeout(() => {
      setIsSubmitting(false);
      console.log('Registration completed:', { email, ...formData });
    }, 2000);
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-slate-50 flex items-center justify-center px-4 sm:px-6 lg:px-8 py-12">
      {/* Signup Card */}
      <div className="w-full max-w-2xl">
        {/* Logo and Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-600 to-blue-800 rounded-2xl mb-4 shadow-xl shadow-blue-600/30">
           <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="9" stroke="white" strokeWidth="1.2" />
                <path d="M6 12c1.5-4 6-6 8-6" stroke="white" strokeWidth="1.2" strokeLinecap="round" />
            </svg>
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Join Aurora</h1>
          <p className="text-gray-600">Request access to the emergency response platform</p>
        </div>

        {/* Progress Indicator */}
        <div className="mb-8">
          <div className="flex items-center justify-center">
            <div className="flex items-center space-x-4">
              <div className={`flex items-center justify-center w-10 h-10 rounded-full ${
                step >= 1 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'
              } font-bold transition`}>
                {step > 1 ? <CheckCircle className="w-6 h-6" /> : '1'}
              </div>
              <div className={`h-1 w-20 ${step >= 2 ? 'bg-blue-600' : 'bg-gray-200'} transition`}></div>
              <div className={`flex items-center justify-center w-10 h-10 rounded-full ${
                step >= 2 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'
              } font-bold transition`}>
                2
              </div>
            </div>
          </div>
          <div className="flex justify-center mt-2 space-x-24">
            <span className="text-xs font-semibold text-gray-600">Verify Email</span>
            <span className="text-xs font-semibold text-gray-600">Complete Profile</span>
          </div>
        </div>

        {/* Step 1: Email Verification */}
        {step === 1 && (
          <div className="bg-white rounded-2xl shadow-2xl p-8 border border-gray-100">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Verify Your Email</h2>
              <p className="text-gray-600">Enter your work email to get started with Aurora</p>
            </div>

            <div className="space-y-5">
              <div>
                <label htmlFor="email" className="block text-md font-semibold text-gray-700 mb-2 text-left mx-2">
                  Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Mail className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={isOtpSent}
                    className={`w-full pl-12 pr-4 py-3 border ${
                      errors.email ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                    } rounded-lg focus:outline-none focus:ring-2 transition text-lg ${
                      isOtpSent ? 'bg-gray-50 cursor-not-allowed' : ''
                    }`}
                    placeholder="your.email@company.com"
                  />
                  {isOtpSent && (
                    <div className="absolute inset-y-0 right-0 pr-4 flex items-center">
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    </div>
                  )}
                </div>
                {errors.email && (
                  <div className="flex items-center mt-2 text-red-600 text-sm">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    <span>{errors.email}</span>
                  </div>
                )}
              </div>

              {!isOtpSent ? (
                <button
                  onClick={handleGetOtp}
                  disabled={isSendingOtp}
                  className="w-full px-6 py-4 bg-blue-600 text-white rounded-lg font-bold text-lg hover:bg-blue-700 transition shadow-xl shadow-blue-600/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                >
                  {isSendingOtp ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                      Sending OTP...
                    </>
                  ) : (
                    <>
                      Get OTP
                      <ArrowRight className="w-5 h-5 ml-2" />
                    </>
                  )}
                </button>
              ) : (
                <>
                  <div>
                    <label htmlFor="otp" className="block text-md font-semibold text-gray-700 mb-2 text-left mx-2">
                      Enter OTP
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <Shield className="h-5 w-5 text-gray-400" />
                      </div>
                      <input
                        id="otp"
                        type="text"
                        value={otp}
                        onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                        onKeyPress={(e) => e.key === 'Enter' && handleVerifyOtp()}
                        className={`w-full pl-12 pr-4 py-3 border ${
                          errors.otp ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                        } rounded-lg focus:outline-none focus:ring-2 transition text-lg tracking-widest text-center font-bold`}
                        placeholder="000000"
                        maxLength={6}
                      />
                    </div>
                    {errors.otp && (
                      <div className="flex items-center mt-2 text-red-600 text-sm">
                        <AlertCircle className="w-4 h-4 mr-1" />
                        <span>{errors.otp}</span>
                      </div>
                    )}
                    <div className="flex items-center justify-between mt-2">
                      <p className="text-xs text-gray-500">
                        OTP sent to {email}
                      </p>
                      <button
                        onClick={() => {
                          setIsOtpSent(false);
                          setOtp('');
                          setErrors({});
                        }}
                        className="text-xs font-semibold text-blue-600 hover:text-blue-700 transition"
                      >
                        Change Email
                      </button>
                    </div>
                  </div>

                  <button
                    onClick={handleVerifyOtp}
                    disabled={isVerifying}
                    className="w-full px-6 py-4 bg-blue-600 text-white rounded-lg font-bold text-lg hover:bg-blue-700 transition shadow-xl shadow-blue-600/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                  >
                    {isVerifying ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                        Verifying OTP...
                      </>
                    ) : (
                      <>
                        Verify OTP
                        <CheckCircle className="w-5 h-5 ml-2" />
                      </>
                    )}
                  </button>
                </>
              )}
            </div>

            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start space-x-3">
                <CheckCircle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-blue-900 mb-1">Why verify your email?</p>
                  <p className="text-xs text-blue-700 leading-relaxed">
                    We'll send a verification code to ensure secure access to your organization's emergency response system.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Full Registration Form */}
        {step === 2  && (
          <div className="bg-white rounded-2xl shadow-2xl p-8 border border-gray-100">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Complete Your Profile</h2>
              <p className="text-gray-600">Tell us about yourself and your organization</p>
            </div>

            <div className="space-y-5">
              {/* Email (Read-only) */}
              <div>
                <label className="block text-md text-left font-semibold text-gray-700 mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Mail className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    type="email"
                    value={email}
                    disabled
                    className="w-full pl-12 pr-4 py-3 border border-gray-200 bg-gray-50 rounded-lg text-gray-600 cursor-not-allowed"
                  />
                  <div className="absolute inset-y-0 right-0 pr-4 flex items-center">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  </div>
                </div>
              </div>

              {/* Name Fields */}
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="firstName" className="block text-md text-left font-semibold text-gray-700 mb-2">
                    First Name
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <User className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      id="firstName"
                      type="text"
                      value={formData.firstName}
                      onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                      className={`w-full pl-12 pr-4 py-3 border ${
                        errors.firstName ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                      } rounded-lg focus:outline-none focus:ring-2 transition`}
                      placeholder="John"
                    />
                  </div>
                  {errors.firstName && (
                    <div className="flex items-center mt-2 text-red-600 text-sm">
                      <AlertCircle className="w-4 h-4 mr-1" />
                      <span>{errors.firstName}</span>
                    </div>
                  )}
                </div>

                <div>
                  <label htmlFor="lastName" className="block text-md text-left font-semibold text-gray-700 mb-2">
                    Last Name
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <User className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      id="lastName"
                      type="text"
                      value={formData.lastName}
                      onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                      className={`w-full pl-12 pr-4 py-3 border ${
                        errors.lastName ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                      } rounded-lg focus:outline-none focus:ring-2 transition`}
                      placeholder="Doe"
                    />
                  </div>
                  {errors.lastName && (
                    <div className="flex items-center mt-2 text-red-600 text-sm">
                      <AlertCircle className="w-4 h-4 mr-1" />
                      <span>{errors.lastName}</span>
                    </div>
                  )}
                </div>
              </div>
            {/* Password Input */}
              <div>
              <label htmlFor="password" className="block text-md text-left font-semibold text-gray-700 mb-2">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="password"
                  type={!showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className={`w-full pl-12 pr-12 py-3 border ${
                    errors.password ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                  } rounded-lg focus:outline-none focus:ring-2 transition`}
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-4 flex items-center text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? (
                    <EyeOff className="h-5" />
                  ) : (
                    <Eye className="h-5" />
                  )}
                </button>
              </div>
              {errors.password && (
                <div className="flex items-center mt-2 text-red-600 text-sm">
                  <AlertCircle className="w-4 h-4 mr-1" />
                  <span>{errors.password}</span>
                </div>
              )}
            </div>  
              {/* Position */}
              <div>
                <label htmlFor="position" className="block text-md font-semibold text-gray-700 mb-2 text-left">
                  Position / Role
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Briefcase className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    id="position"
                    type="text"
                    value={formData.position}
                    onChange={(e) => setFormData({ ...formData, position: e.target.value })}
                    className={`w-full pl-12 pr-4 py-3 border ${
                      errors.position ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                    } rounded-lg focus:outline-none focus:ring-2 transition`}
                    placeholder="Safety Supervisor"
                  />
                </div>
                {errors.position && (
                  <div className="flex items-center mt-2 text-red-600 text-sm">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    <span>{errors.position}</span>
                  </div>
                )}
              </div>

              {/* Company Name */}
              <div>
                <label htmlFor="companyName" className="block text-md text-left font-semibold text-gray-700 mb-2">
                  Company Name
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Building className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    id="companyName"
                    type="text"
                    value={formData.companyName}
                    onChange={(e) => setFormData({ ...formData, companyName: e.target.value })}
                    className={`w-full pl-12 pr-4 py-3 border ${
                      errors.companyName ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                    } rounded-lg focus:outline-none focus:ring-2 transition`}
                    placeholder="Acme Industrial Corp"
                  />
                </div>
                {errors.companyName && (
                  <div className="flex items-center mt-2 text-red-600 text-sm">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    <span>{errors.companyName}</span>
                  </div>
                )}
              </div>

              {/* Company Manual Upload */}
              <div>
                <label className="block text-md text-left font-semibold text-gray-700 mb-2">
                  SOP/Safety Manual of your company (PDF)
                </label>
                
                {!formData.companyManual ? (
                  <div className={`border-2 border-dashed ${
                    errors.file ? 'border-red-500' : 'border-gray-300'
                  } rounded-lg p-6 text-center hover:border-blue-500 transition cursor-pointer`}>
                    <input
                      type="file"
                      accept=".pdf"
                      onChange={handleFileChange}
                      className="hidden"
                      id="file-upload"
                    />
                    <label htmlFor="file-upload" className="cursor-pointer">
                      <Upload className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                      <p className="text-md font-semibold text-gray-700 mb-1">
                        Click to upload or drag and drop
                      </p>
                      <p className="text-xs text-gray-500">
                        PDF file up to 10MB
                      </p>
                    </label>
                  </div>
                ) : (
                  <div className="border-2 border-green-500 bg-green-50 rounded-lg p-4 flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-green-500 rounded-lg flex items-center justify-center">
                        <FileText className="w-6 h-6 text-white" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-900">{formData.companyManual.name}</p>
                        <p className="text-xs text-gray-600">
                          {(formData.companyManual.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={removeFile}
                      className="w-8 h-8 bg-red-500 hover:bg-red-600 rounded-lg flex items-center justify-center text-white transition"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                )}
                
                {errors.file && (
                  <div className="flex items-center mt-2 text-red-600 text-sm">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    <span>{errors.file}</span>
                  </div>
                )}
                
                <p className="text-xs text-gray-500 mt-2">
                  Upload your company's safety procedures manual. Aurora will use this to provide accurate guidance.
                </p>
              </div>
              {errors.tempToken && (
                <div className="flex items-center mt-2 text-red-600 text-sm">
                  <AlertCircle className="w-4 h-4 mr-1" />
                  <span>{errors.tempToken}</span>
                </div>
              )}
              
              
              {/* Submit Button */}
              <button
              type='button'
                onClick={()=>handleSubmit()}
                disabled={isSubmitting}
                className="w-full px-6 py-4 bg-blue-600 text-white rounded-lg font-bold text-lg hover:bg-blue-700 transition shadow-xl shadow-blue-600/30 disabled:opacity-50 cursor-pointer flex items-center justify-center"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                    Creating Account...
                  </>
                ) : (
                  <>
                    Complete Registration
                    <CheckCircle className="w-5 h-5 ml-2" />
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Back to Login Link */}
        <div className="text-center mt-6">
          <p className="text-gray-600">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-blue-600 hover:text-blue-700 transition">
              Log In
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}