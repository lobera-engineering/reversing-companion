#include <stdlib.h>
#include <stdio.h>

void main(){
char buffer[500];
FILE *fp;
int lineno = 0;
if ((fp = fopen("myinputfile.txt","r")) == NULL)
{
        printf("Could not open myinputfile.txt\n");
        exit(1);
}

while ( !feof(fp))
{
        // read in the line and make sure it was successful
        if (fgets(buffer,500,fp) != NULL)
        {
                printf("%d: %s",lineno++,buffer);
        }
}
}
