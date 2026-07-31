# Frontend — Architecture Reference

React (CRA/craco) + Tailwind + shadcn/ui client for the Integrated Patient
Data Retrieval System. JWT-authenticated (V3) — every route past login is
gated by `ProtectedRoute`, and every API call carries the token issued at
login.

## Architecture Overview

```mermaid
graph TB
    LOGIN["/  — LoginPage\nJWT login"]
    WELCOME["/welcome — WelcomePage"]
    SEARCH["/search — SearchPage\npatient search by ID or name"]
    RESULTS["/results — ResultsPage / ResultsPageDepartments\npatient record view"]
    DEPT["/department/:name — DepartmentView\ndept-wide record browsing"]
    ANALYTICS["/analytics — AnalyticsPage / AnalyticsPageWithCharts"]
    MODAL["DeepSearchModal — DocAssist chat\nQ&A, image/PDF upload, voice output"]
    API["FastAPI backend\n/api/deep-query · /api/analyze-document"]

    LOGIN --> WELCOME --> SEARCH --> RESULTS
    RESULTS --> DEPT
    RESULTS --> ANALYTICS
    RESULTS -.->|open| MODAL
    MODAL -->|JWT-authenticated request| API
```

`ProtectedRoute` (`src/components/ProtectedRoute.jsx`) wraps every route
except `/` — it checks for a valid JWT and redirects to login if missing.
`Header.jsx` renders on every authenticated page (patient context, logout).
`DeepSearchModal.jsx` is DocAssist — the AI chat surface — reachable from the
results view, and is the only component that calls `/api/deep-query` and
`/api/analyze-document`.

## Directory Layout

```
frontend/src/
├── App.js                    # BrowserRouter + route definitions
├── components/
│   ├── Header.jsx             # Top nav, patient context, logout
│   ├── DeepSearchModal.jsx    # DocAssist chat — AI Q&A + image/PDF upload
│   └── ProtectedRoute.jsx     # JWT gate on all routes except /
├── pages/
│   ├── LoginPage.jsx
│   ├── WelcomePage.jsx
│   ├── SearchPage.jsx
│   ├── ResultsPage.jsx / ResultsPageDepartments.jsx
│   ├── DepartmentView.jsx
│   └── AnalyticsPage.jsx / AnalyticsPageWithCharts.jsx
├── hooks/use-toast.js
└── lib/utils.js
```

---

# Getting Started with Create React App

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open <http://localhost:3000> to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: <https://facebook.github.io/create-react-app/docs/code-splitting>

### Analyzing the Bundle Size

This section has moved here: <https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size>

### Making a Progressive Web App

This section has moved here: <https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app>

### Advanced Configuration

This section has moved here: <https://facebook.github.io/create-react-app/docs/advanced-configuration>

### Deployment

This section has moved here: <https://facebook.github.io/create-react-app/docs/deployment>

### `npm run build` fails to minify

This section has moved here: <https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify>
