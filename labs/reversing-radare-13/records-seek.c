#include <sys/sendfile.h>
#include <sys/stat.h>
#include <errno.h>
#include <unistd.h>
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


int main () 
{ 
    int infile, outfile; 
    struct person input; 
      
    infile = open ("person.dat", O_RDONLY , 0644); 
    lseek(infile, 1*sizeof(struct person), SEEK_CUR);
    read(infile, &input, sizeof(struct person));

    printf("second person val = %d, %s, %s \n", input.id, input.fname, input.lname);
 
    close (infile); 
  
    return 0; 
}
