import { apiConnector } from '../apiConnector';
import { activeEndpoints } from '../apis';

const { GET_CONVERSATION,GET_ACTIVE_CALLS} = activeEndpoints;
export async function fetchConversationUsingId(conversationId,token){
    try{
        console.log("Fetch Conversation Service :",GET_CONVERSATION," ",conversationId,'token',token);
        const response = await apiConnector("GET",GET_CONVERSATION+conversationId,null,{
        Authorization: `Bearer ${token}`,
      })  
        console.log("Fetch Conversation Response",response);
        return response?.data;
    }
    catch(error){
        console.log(error);
        return null;
    }
}

export async function fetchConversations(token,user){
    try{
        console.log("Fetch Conversation Service :",GET_CONVERSATION," ",'token',token);
        const response = await apiConnector("GET",GET_ACTIVE_CALLS,{
            email:user.email,
            password:localStorage.getItem("password")
        },{
        Authorization: `Bearer ${token}`,
      })  
        console.log("Fetch Conversation Response",response);
        return response?.data;
    }
    catch(error){
        console.log(error);
        return null;
    }
}