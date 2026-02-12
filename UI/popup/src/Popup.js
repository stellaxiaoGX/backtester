import React from "react";
import "./Popup.css"; // We'll style it separately

// Popup component
export default function Popup({ isOpen, onClose, children }) {
  if (!isOpen) return null; // Don't render if not open

  return (
    <div className="popup-overlay" onClick={onClose}>
      <div
        className="popup-content"
        onClick={(e) => e.stopPropagation()} // Prevent closing when clicking inside
      >
        <button className="popup-close" onClick={onClose}>
          &times;
        </button>
        {children}
      </div>
    </div>
  );
}
