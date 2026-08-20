import keycloak from 'keycloak-js';

const keycloakInstance = new keycloak({
    url: "http://localhost:8080" ,
    realm:  "insurance",
    clientId:  "insurance-frontend",
    });

    export default keycloakInstance;