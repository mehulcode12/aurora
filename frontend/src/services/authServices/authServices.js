import { authEndpoints } from '../apis';
import { apiConnector } from '../apiConnector';

const { GET_OTP, SIGN_UP,VERIFY_OTP,LOG_IN } = authEndpoints;
export async function getOtp(email){
    try{
        console.log("OTP Service",GET_OTP," ",email);
            const response = await apiConnector("POST",GET_OTP,{
                email:email
            })
            console.log("OTP Response",response);
            return response;
        }
        catch(error){
            console.log(error);
            return null;
        }
}

export async function verifyOtp(email,otp){
    try{
            console.log("Verify OTP Service",VERIFY_OTP," ",email," ",otp);
            const response = await apiConnector("POST",VERIFY_OTP,{                 
                email:JSON.stringify(email),
                otp:JSON.stringify(otp)
            })
            console.log("Verify OTP Response",response);
            return response;
        }
        catch(error){
            console.log(error);
            return error;
        }
}



export async function signUp(email,formData){
        try{
            console.log("SignUp Service :",SIGN_UP," ",email," ",formData);
            const response = await apiConnector("POST",SIGN_UP,{
                email:email,
                name:formData.firstName+" "+formData.lastName,
                password:formData.password,
                temp_token:formData.tempToken,
                designation:formData.position,
                company_name:formData.companyName,
                files:formData.companyManual
            })
            console.log("SignUp Response",response);
            return response;
        }
        catch(error){
            console.log(error);
            return error;
        }
}

export async function logIn(email,password){
    try{
        // console.log("Login Service :",LOG_IN," ",email," ",password);
        var response = await apiConnector("POST",LOG_IN,{
            email:email,
            password:password
        })
        return response;
    }
    catch(error){
        console.log(error);
        return error;
    }
}