import axios from 'axios'

//creating an instance of axios to use it globally
export const axiosInstance = axios.create({});

//exporting the apiConnector function to use it in other files
//this function will take the method, url, body, headers and params as arguments and return the response
export const apiConnector = (method, url, body, headers,params) => {
    // console.log("BODY DATA ",body)
    return axiosInstance({
        method:`${method}`,
        url:`${url}`,
        data:body?body:null,
        headers:headers? headers: null,
        params: params? params:null,
    })
};
