
const BASE_URL = "https://api-x1tb.onrender.com";


export const authEndpoints = {
    GET_OTP: BASE_URL+"/get-otp",
    VERIFY_OTP: BASE_URL+"/verify-otp",
    SIGN_UP: BASE_URL+"/sign-up",
    LOG_IN: BASE_URL+"/login",
    PROVIDE_ACCESS: BASE_URL + "/logout",
}

export const activeEndpoints = {
    GET_ACTIVE_CALLS: BASE_URL + "/get-active-calls",
    GET_CONVERSATION: BASE_URL + "/api/conversation/",
    STREAM_LIVE_CONVERSATION:BASE_URL+"/api/conversation/:conversation_id/stream"
}