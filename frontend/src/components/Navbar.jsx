import React from 'react'
import { Link } from 'react-router-dom'

const Navbar = () => {
  return (
    <header className="w-full border-b border-slate-200 bg-slate-50 opacity-100 fixed -mt-12 px-10 -ml-8">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-sky-700 to-indigo-700 flex items-center justify-center shadow-md">
              {/* Aurora mark (simplified) */}
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="9" stroke="white" strokeWidth="1.2" />
                <path d="M6 12c1.5-4 6-6 8-6" stroke="white" strokeWidth="1.2" strokeLinecap="round" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-extrabold tracking-tight">Aurora</h1>
              {/* <p className="text-xs text-slate-500 -mt-1">AI Field Assistant — Safety in Seconds</p> */}
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-5 text-sm text-slate-900">
            <a className="hover:text-slate-500 cursor-pointer" href='#howitworks'>How it works</a>
            <a className="hover:text-slate-500 cursor-pointer" href='#usecase'>Use cases</a>
            <a className="hover:text-slate-500 cursor-pointer">Security</a>
            <div className='flex gap-4 text-slate-200 '>
                <Link to="/signup" className=" px-4 py-2 rounded-md border border-slate-800 text-sm hover:border-slate-500 opacity-90 hover:opacity-100 bg-slate-700 hover:bg-slate-900">Sign Up</Link>
                <Link to= "/login" className=" px-4 py-2 rounded-md border border-slate-800 text-sm hover:border-slate-500 opacity-90 hover:opacity-100 bg-slate-700 hover:bg-slate-900">Log In</Link>
            </div>
            {/* <button className="ml-2 px-4 py-2 rounded-md bg-sky-700 text-white font-semibold">Request Demo</button> */}
          </nav>
        </div>
      </header>
  )
}

export default Navbar