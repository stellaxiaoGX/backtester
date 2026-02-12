import React, { useEffect } from "react";

function PopupWindow() {
  useEffect(() => {
    const popup = window.open(
      "",
      "Popup",
      "width=400,height=300,left=200,top=200"
    );

    if (popup) {
      popup.document.write(`
        <html>
          <head>
            <title>React Popup</title>
            <style>
              body { font-family: Arial; padding: 20px; }
              button { padding: 8px 12px; }
            </style>
          </head>
          <body>
            <h2>Standalone Popup Window</h2>
            <p>This is a separate browser window.</p>
            <button onclick="window.close()">Close</button>
          </body>
        </html>
      `);
      popup.document.close();
    }
  }, []);

  return null; // Nothing rendered in main page
}

export default PopupWindow;
