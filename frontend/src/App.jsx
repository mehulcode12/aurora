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

function App() {
  

  return (
    <>
      {/* <div className='text-[50px]'>Aurora</div> */}
      <Navbar/>
      <Routes>
        <Route path='/' element={<Home/>}/>
        <Route path='/login' element={<Login/>}/>
        <Route path='/signup' element={<SignUp/>}/>
        <Route path='/admin' element={<AdminDashboard/>}/>
      </Routes>
      {/* <Home /> */}
    </>
  )
}

export default App
