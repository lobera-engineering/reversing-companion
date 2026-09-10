#include <stdio.h> 
#include <stdlib.h> 
#include <fcntl.h>
#include <stdlib.h>
struct person  
{ 
    int id; 
    char fname[20]; 
    char lname[20]; 
}; 


void cryp(char  arr[]){
    char k[20] = "01234567890123456789";
    for(int i = 0; i < sizeof(arr); i ++){
        arr[i] ^= k[i];
    }
    arr[sizeof(arr)-1]='\0';

}
int main () 
{ 
    int infile, outfile; 
    struct person input; 
      
    infile = open ("person.dat", O_RDONLY , 0644); 
    outfile = open ("person.cry", O_WRONLY | O_CREAT, 0644);
    while(read(infile, &input, sizeof(struct person))){ 
        cryp(input.fname);
        cryp(input.lname);

        write(outfile, &input, sizeof(struct person));
    }
    close (infile); 
  
    return 0; 
}
