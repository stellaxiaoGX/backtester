import './App.css';
import React, { useState } from "react";
import Popup from "./Popup";

export default function App() {
  const [isPopupOpen, setIsPopupOpen] = useState(false);

  return (
    <div style={{ padding: "20px" }}>
      <h1>React Popup Example</h1>
      <button onClick={() => setIsPopupOpen(true)}>Open Popup</button>

      <Popup isOpen={isPopupOpen} onClose={() => setIsPopupOpen(false)}>
        <h2>Hello from Popup!</h2>
        <p>This is a simple popup window in React.</p>
      </Popup>
    </div>
  );
}
