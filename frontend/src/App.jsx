import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import Home from './pages/Home'
import Login from './pages/LogIn'
import SignUp from './pages/SignUp'
import {Route,Routes} from 'react-router-dom'
import Navbar from './components/Navbar'
import AdminDashboard from './pages/AdminDashboard'
import { createContext } from 'react'

const UserContext = createContext({
  token:localStorage.getItem("token")?(localStorage.getItem("token")):null,
  user:localStorage.getItem("user")?(localStorage.getItem("user")):null,
});

function App() {
  const [token,setToken] = useState(localStorage.getItem("token")?(localStorage.getItem("token")):null)
  const [user,setUser]  = useState(localStorage.getItem("user")?(localStorage.getItem("user")):null);
  return (
    <>
      {/* <div className='text-[50px]'>Aurora</div> */}
      <UserContext.Provider value={{token,setToken,user,setUser}}>
      <Navbar/>
      <Routes>
        <Route path='/' element={<Home/>}/>
        <Route path='/login' element={<Login/>}/>
        <Route path='/signup' element={<SignUp/>}/>
        <Route path='/admin' element={<AdminDashboard/>}/>
      </Routes>
      </UserContext.Provider>
      {/* <Home /> */}
    </>
  )
}

export default App;
export {UserContext};
