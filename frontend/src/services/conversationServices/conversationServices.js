import { apiConnector } from '../apiConnector';
import { activeEndpoints } from '../apis';

const { GET_CONVERSATION,GET_ACTIVE_CONVERSATIONS,GET_ACTIVE_CALLS,GET_CALL_CONVERSATION} = activeEndpoints;
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
        const response = await apiConnector("GET",GET_ACTIVE_CONVERSATIONS,null,{
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

export async function fetchCalls(token){
    try{
        const response = await apiConnector("GET",GET_ACTIVE_CALLS,null,{
        Authorization: `Bearer ${token}`,
      })  
        console.log("Fetch Call Response",response);
        return response?.data;
    }
    catch(error){
        console.log(error);
        return null;
    }
}

export async function fetchCallUsingId(conversationId,token){
    try{
        // console.log("Fetch Conversation Service :",GET_CALL_CONVERSATION," ",conversationId,'token',token);
        const response = await apiConnector("GET",GET_CALL_CONVERSATION+"/"+"V9tndVGPrPumpk2OPOwU"+"/conversation",null,{
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